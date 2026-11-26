import json
import re
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Ticket
from .services import generer_demo

STAFF = {'HTTP_X_STAFF_CODE': 'test-code'}


@override_settings(STAFF_ACCESS_CODE='test-code')
class ParcoursTest(TestCase):
    def setUp(self):
        self.ev = generer_demo()

    def post(self, url, data, **extra):
        return self.client.post(url, json.dumps(data), content_type='application/json', **extra)

    def creer(self, tel='77 123 45 67'):
        r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': tel})
        self.assertEqual(r.status_code, 201)
        return r.json()['paiement']

    def acheter(self, transaction='T_ABC123XYZ'):
        ref = self.creer()['reference']
        r = self.post(f'/api/paiements/{ref}/declarer', {'transaction': transaction})
        self.assertEqual(r.json()['paiement']['statut'], 'a_verifier')
        r = self.post(f'/api/staff/paiements/{ref}/valider', {}, **STAFF)
        return r.json()['paiement']['ticket_id']

    def test_lien_wave_avec_montant(self):
        p = self.creer()
        self.assertTrue(p['wave_url'].startswith('https://pay.wave.com/m/'))
        self.assertIn('amount=2500', p['wave_url'])

    def test_lien_wave_disponible_avant_le_paiement(self):
        # Le bouton de l'accueil ouvre Wave directement : le lien (montant pré-rempli) doit être connu d'avance
        url = self.client.get('/api/evenement').json()['wave_url']
        self.assertTrue(url.startswith('https://pay.wave.com/m/'))
        self.assertIn('amount=2500', url)

    def test_pas_de_billet_avant_validation(self):
        ref = self.creer()['reference']
        self.post(f'/api/paiements/{ref}/declarer', {'transaction': 'T_ABC123XYZ'})
        self.assertIsNone(self.client.get(f'/api/paiements/{ref}').json()['paiement']['ticket_id'])
        self.assertEqual(Ticket.objects.exclude(statut='disponible').count(), 0)

    @override_settings(PAIEMENT_SIMULE=False)
    def test_simulation_desactivee_en_production(self):
        ref = self.creer()['reference']
        self.assertEqual(self.post(f'/api/paiements/{ref}/simuler', {}).status_code, 404)

    @override_settings(PAIEMENT_SIMULE=True)
    def test_simulation_emet_le_billet(self):
        ref = self.creer()['reference']
        p = self.post(f'/api/paiements/{ref}/simuler', {}).json()['paiement']
        self.assertEqual(p['statut'], 'reussi')
        self.assertIsNotNone(p['ticket_id'])

    def test_achat_puis_scan(self):
        ticket_id = self.acheter()
        qr = self.client.get(f'/api/tickets/{ticket_id}').json()['ticket']['qr']

        self.assertEqual(self.post('/api/staff/scan', {'qr': qr}, **STAFF).json()['resultat'], 'valide')
        self.assertEqual(self.post('/api/staff/scan', {'qr': qr}, **STAFF).json()['resultat'], 'utilise')

        stats = self.client.get('/api/staff/stats', **STAFF).json()['stats']
        self.assertEqual((stats['vendus'], stats['scannes'], stats['restants']), (1, 1, 749))
        self.assertEqual(stats['par_type']['prevente']['restants'], 399)
        self.assertEqual(stats['par_type']['jour_j']['restants'], 200)

    def test_transaction_reutilisee_refusee(self):
        self.acheter('T_UNIQUE0001')
        ref = self.creer()['reference']
        r = self.post(f'/api/paiements/{ref}/declarer', {'transaction': 't_unique0001'})
        self.assertEqual(r.status_code, 409)

    def test_declaration_sans_transaction(self):
        ref = self.creer()['reference']
        r = self.post(f'/api/paiements/{ref}/declarer', {})
        self.assertEqual(r.json()['paiement']['statut'], 'a_verifier')
        self.assertIsNotNone(self.post(f'/api/staff/paiements/{ref}/valider', {}, **STAFF).json()['paiement']['ticket_id'])

    def test_rejet(self):
        ref = self.creer()['reference']
        self.post(f'/api/paiements/{ref}/declarer', {'transaction': 'T_FAUX12345'})
        r = self.post(f'/api/staff/paiements/{ref}/rejeter', {}, **STAFF)
        self.assertEqual(r.json()['paiement']['statut'], 'echoue')
        self.assertEqual(Ticket.objects.exclude(statut='disponible').count(), 0)

    def test_validation_renvoie_le_code_du_billet(self):
        ref = self.creer()['reference']
        self.post(f'/api/paiements/{ref}/declarer', {})
        p = self.post(f'/api/staff/paiements/{ref}/valider', {}, **STAFF).json()['paiement']
        self.assertEqual(p['code'], 'PV-001')

    def test_double_validation_ne_vend_pas_deux_billets(self):
        ref = self.creer()['reference']
        self.post(f'/api/paiements/{ref}/declarer', {'transaction': 'T_ABC123XYZ'})
        self.post(f'/api/staff/paiements/{ref}/valider', {}, **STAFF)
        self.post(f'/api/staff/paiements/{ref}/valider', {}, **STAFF)
        self.assertEqual(Ticket.objects.exclude(statut='disponible').count(), 1)

    def test_validation_reservee_au_personnel(self):
        ref = self.creer()['reference']
        self.assertEqual(self.post(f'/api/staff/paiements/{ref}/valider', {}).status_code, 401)

    def test_qr_compact(self):
        ticket_id = self.acheter()
        qr = self.client.get(f'/api/tickets/{ticket_id}').json()['ticket']['qr']
        self.assertTrue(qr.startswith('B1.'))
        self.assertLessEqual(len(qr), 42)  # tient dans un QR version 3 (29x29 modules)

    def test_ancien_format_json_accepte(self):
        from .models import signer
        ticket_id = self.acheter()
        ancien = json.dumps({'id': ticket_id, 'sig': signer(ticket_id)})
        self.assertEqual(self.post('/api/staff/scan', {'qr': ancien}, **STAFF).json()['resultat'], 'valide')

    def test_qr_compact_falsifie(self):
        ticket_id = self.acheter()
        qr = self.client.get(f'/api/tickets/{ticket_id}').json()['ticket']['qr']
        faux = qr[:-3] + ('AAA' if not qr.endswith('AAA') else 'BBB')
        self.assertEqual(self.post('/api/staff/scan', {'qr': faux}, **STAFF).json()['resultat'], 'invalide')

    def test_qr_falsifie(self):
        ticket_id = self.acheter()
        faux = json.dumps({'id': ticket_id, 'sig': '0' * 20})
        self.assertEqual(self.post('/api/staff/scan', {'qr': faux}, **STAFF).json()['resultat'], 'invalide')

    def test_staff_protege(self):
        self.assertEqual(self.client.get('/api/staff/stats').status_code, 401)

    def test_telephone_invalide(self):
        r = self.post('/api/paiements', {'nom': 'Awa', 'telephone': '12345'})
        self.assertEqual(r.status_code, 400)

    # --- Prévente / Jour J -------------------------------------------------

    def passer_au_jour_j(self):
        self.ev.fin_prevente = timezone.now() - timedelta(minutes=1)
        self.ev.save()

    def test_six_cents_places_en_deux_series(self):
        self.assertEqual(Ticket.objects.filter(type='prevente').count(), 400)
        self.assertEqual(Ticket.objects.filter(type='jour_j').count(), 200)

    def test_prevente_avant_la_date(self):
        d = self.client.get('/api/evenement').json()
        self.assertEqual((d['tarif']['type'], d['tarif']['prix'], d['tarif']['complet']), ('prevente', 2500, False))
        # Jauge privée : aucun chiffre de places dans l'API publique
        self.assertNotIn('restants', d['tarif'])
        self.assertFalse({'capacite', 'quota_prevente', 'quota_jour_j'} & set(d['evenement']))
        ticket = self.client.get(f'/api/tickets/{self.acheter()}').json()['ticket']
        self.assertEqual((ticket['type'], ticket['prix'], ticket['code']), ('prevente', 2500, 'PV-001'))

    def test_jour_j_pas_de_vente_en_ligne(self):
        self.passer_au_jour_j()
        d = self.client.get('/api/evenement').json()
        self.assertEqual((d['tarif']['type'], d['vente_en_ligne']), ('jour_j', False))
        r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': '771234567'})
        self.assertEqual(r.status_code, 409)
        self.assertIn('sur place', r.json()['erreur'])

    def test_prevente_payee_puis_validee_le_jour_j_reste_prevente(self):
        ref = self.creer()['reference']
        self.post(f'/api/paiements/{ref}/declarer', {})
        self.passer_au_jour_j()
        p = self.post(f'/api/staff/paiements/{ref}/valider', {}, **STAFF).json()['paiement']
        self.assertEqual(Ticket.objects.get(pk=p['ticket_id']).type, 'prevente')

    def test_prevente_epuisee(self):
        Ticket.objects.filter(type='prevente').update(statut='vendu')
        r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': '771234567'})
        self.assertEqual(r.status_code, 409)
        self.assertIn('Prévente épuisée', r.json()['erreur'])

    def test_vente_guichet_entree_immediate(self):
        r = self.post('/api/staff/vente-guichet', {'type': 'jour_j', 'nom': 'Moussa'}, **STAFF)
        self.assertEqual(r.status_code, 201)
        t = r.json()['ticket']
        self.assertEqual((t['type'], t['statut'], t['code']), ('jour_j', 'utilise', 'JJ-001'))
        # Le billet ne peut pas resservir
        self.assertEqual(self.post('/api/staff/scan', {'qr': t['qr']}, **STAFF).json()['resultat'], 'utilise')
        stats = self.client.get('/api/staff/stats', **STAFF).json()['stats']
        self.assertEqual(stats['par_type']['jour_j']['recette'], 3000)

    def test_vente_guichet_reservee_au_personnel(self):
        self.assertEqual(self.post('/api/staff/vente-guichet', {'type': 'jour_j'}).status_code, 401)

    # --- VIP / VVIP --------------------------------------------------------

    def test_series_vip(self):
        self.assertEqual(Ticket.objects.filter(type='vip').count(), 100)
        self.assertEqual(Ticket.objects.filter(type='vvip').count(), 50)
        d = self.client.get('/api/evenement').json()
        self.assertEqual([(t['type'], t['prix'], t['en_vente']) for t in d['tarifs_vip']], [('vip', 10000, True), ('vvip', 25000, True)])
        self.assertIn('amount=25000', d['tarifs_vip'][1]['wave_url'])
        self.assertFalse({'quota_vip', 'quota_vvip'} & set(d['evenement']))

    def test_achat_vip_et_vvip(self):
        for type_billet, prix, code in (('vip', 10000, 'VIP-001'), ('vvip', 25000, 'VVIP-001')):
            r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': '771234567', 'type': type_billet})
            self.assertEqual(r.status_code, 201)
            p = r.json()['paiement']
            self.assertEqual((p['type'], p['montant']), (type_billet, prix))
            self.assertIn(f'amount={prix}', p['wave_url'])
            self.post(f"/api/paiements/{p['reference']}/declarer", {})
            v = self.post(f"/api/staff/paiements/{p['reference']}/valider", {}, **STAFF).json()['paiement']
            self.assertEqual(v['code'], code)
        stats = self.client.get('/api/staff/stats', **STAFF).json()['stats']['par_type']
        self.assertEqual((stats['vip']['recette'], stats['vvip']['recette']), (10000, 25000))

    def test_vip_en_vente_le_jour_j(self):
        self.passer_au_jour_j()
        r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': '771234567', 'type': 'vip'})
        self.assertEqual(r.status_code, 201)

    def test_vip_complet_et_apres_concert(self):
        Ticket.objects.filter(type='vvip').update(statut='vendu')
        r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': '771234567', 'type': 'vvip'})
        self.assertEqual(r.status_code, 409)
        self.ev.date = timezone.now() - timedelta(minutes=1)
        self.ev.save()
        r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': '771234567', 'type': 'vip'})
        self.assertEqual(r.status_code, 409)

    def test_type_invalide(self):
        r = self.post('/api/paiements', {'nom': 'Awa Ba', 'telephone': '771234567', 'type': 'gratuit'})
        self.assertEqual(r.status_code, 400)

    def test_quota_vip_augmente_cree_les_billets(self):
        from .services import creer_billets_manquants
        self.ev.quota_vip = 120
        self.ev.save()
        creer_billets_manquants(self.ev)
        self.assertEqual(Ticket.objects.filter(type='vip').count(), 120)
        self.ev.refresh_from_db()
        self.assertEqual(self.ev.capacite, 770)

    # --- Billets papier Jour J ---------------------------------------------

    def imprimer(self):
        r = self.client.post('/api/staff/billets-physiques', **STAFF)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        return r

    def test_impression_des_200_billets_jour_j(self):
        r = self.imprimer()
        pages = re.findall(rb'/Type\s*/Page[^s]', r.content)
        self.assertEqual(len(pages), 50)  # 200 billets, 4 par page
        papier = Ticket.objects.filter(type='jour_j', physique=True)
        self.assertEqual(papier.count(), 200)
        self.assertFalse(papier.exclude(statut='vendu').exists())
        self.assertFalse(Ticket.objects.filter(type='prevente', physique=True).exists())

    def test_billet_papier_entre_une_seule_fois(self):
        self.imprimer()
        qr = Ticket.objects.get(type='jour_j', numero=7).qr_payload
        r1 = self.post('/api/staff/scan', {'qr': qr}, **STAFF).json()
        self.assertEqual((r1['resultat'], r1['ticket']['code']), ('valide', 'JJ-007'))
        self.assertEqual(self.post('/api/staff/scan', {'qr': qr}, **STAFF).json()['resultat'], 'utilise')

    def test_reimpression_sans_effet_sur_les_billets_utilises(self):
        self.imprimer()
        qr = Ticket.objects.get(type='jour_j', numero=1).qr_payload
        self.post('/api/staff/scan', {'qr': qr}, **STAFF)
        self.imprimer()
        self.assertEqual(Ticket.objects.get(type='jour_j', numero=1).statut, 'utilise')

    def test_recette_papier_comptee_a_l_entree(self):
        self.imprimer()
        for n in (1, 2):
            self.post('/api/staff/scan', {'qr': Ticket.objects.get(type='jour_j', numero=n).qr_payload}, **STAFF)
        jj = self.client.get('/api/staff/stats', **STAFF).json()['stats']['par_type']['jour_j']
        self.assertEqual((jj['physiques'], jj['scannes'], jj['recette']), (200, 2, 6000))

    def test_impression_reservee_au_personnel(self):
        self.assertEqual(self.client.post('/api/staff/billets-physiques').status_code, 401)

    # --- Remise à zéro et design du billet papier -----------------------------

    def test_remise_a_zero_des_tests_jour_j_rend_les_200_billets(self):
        # Situation du serveur : 2 billets Jour J vendus au guichet pour tester
        for nom in ('Test 1', 'Test 2'):
            self.post('/api/staff/vente-guichet', {'type': 'jour_j', 'nom': nom}, **STAFF)
        jj = self.client.get('/api/staff/stats', **STAFF).json()['stats']['par_type']['jour_j']
        self.assertEqual(jj['hors_papier'], 2)

        r = self.post('/api/staff/billets-jour-j/reinitialiser-tests', {}, **STAFF).json()
        self.assertEqual(r['reinitialises'], ['JJ-001', 'JJ-002'])
        self.imprimer()
        self.assertEqual(Ticket.objects.filter(type='jour_j', physique=True, statut='vendu').count(), 200)

    def test_remise_a_zero_billet_papier_scanne(self):
        self.imprimer()
        t = Ticket.objects.get(type='jour_j', numero=5)
        self.post('/api/staff/scan', {'qr': t.qr_payload}, **STAFF)
        self.post('/api/staff/billets-jour-j/reinitialiser-tests', {}, **STAFF)
        t.refresh_from_db()
        self.assertEqual((t.statut, t.physique, t.date_scan), ('vendu', True, None))
        # Il rentre de nouveau
        self.assertEqual(self.post('/api/staff/scan', {'qr': t.qr_payload}, **STAFF).json()['resultat'], 'valide')

    def test_reinitialiser_un_billet_vendu_en_ligne(self):
        ticket_id = self.acheter()
        r = self.post(f'/api/staff/tickets/{ticket_id}/reinitialiser', {}, **STAFF)
        self.assertEqual(r.json()['ticket']['statut'], 'disponible')
        self.assertEqual(self.client.get(f'/api/tickets/{ticket_id}').status_code, 404)

    def test_design_papier(self):
        d = self.client.get('/api/staff/billets-physiques/design', **STAFF).json()
        self.assertEqual(d['design']['bandeau'], 'JOUR J')
        self.assertEqual(d['design']['titre'], 'Dip Doundou Guiss')
        r = self.post('/api/staff/billets-physiques/design', {'design': {'titre': 'DIP EN LIVE', 'couleur': '#112233'}}, **STAFF)
        self.assertEqual((r.json()['design']['titre'], r.json()['design']['couleur']), ('DIP EN LIVE', '#112233'))
        self.assertEqual(r.json()['design']['prix'], '3 000 FCFA')  # non modifié = défaut
        bad = self.post('/api/staff/billets-physiques/design', {'design': {'couleur': 'rouge'}}, **STAFF)
        self.assertEqual(bad.status_code, 400)

    def test_apercu_sans_emission(self):
        r = self.client.post('/api/staff/billets-physiques/apercu', **STAFF)
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertEqual(len(re.findall(rb'/Type\s*/Page[^s]', r.content)), 1)
        self.assertFalse(Ticket.objects.filter(physique=True).exists())

    # --- Billets papier Prévente --------------------------------------------

    def imprimer_prevente(self, nombre=None):
        url = '/api/staff/billets-physiques?type=prevente' + (f'&nombre={nombre}' if nombre else '')
        r = self.client.post(url, **STAFF)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        return r

    def test_cent_billets_prevente_papier(self):
        r = self.imprimer_prevente()
        self.assertEqual(len(re.findall(rb'/Type\s*/Page[^s]', r.content)), 25)  # 100 billets, 4 par page
        papier = Ticket.objects.filter(type='prevente', physique=True)
        self.assertEqual(papier.count(), 100)
        self.assertEqual(sorted(papier.values_list('numero', flat=True))[:2], [301, 302])
        self.assertFalse(Ticket.objects.filter(type='jour_j', physique=True).exists())
        # Réimpression : toujours les mêmes 100 billets
        self.imprimer_prevente()
        self.assertEqual(Ticket.objects.filter(type='prevente', physique=True).count(), 100)

    def test_vente_en_ligne_continue_apres_impression_prevente(self):
        self.imprimer_prevente()
        ticket = self.client.get(f'/api/tickets/{self.acheter()}').json()['ticket']
        self.assertEqual((ticket['code'], ticket['physique']), ('PV-001', False))
        pv = self.client.get('/api/staff/stats', **STAFF).json()['stats']['par_type']['prevente']
        self.assertEqual((pv['physiques'], pv['restants']), (100, 299))

    def test_billet_papier_prevente_scanne(self):
        self.imprimer_prevente()
        t = Ticket.objects.get(type='prevente', numero=350)
        r = self.post('/api/staff/scan', {'qr': t.qr_payload}, **STAFF).json()
        self.assertEqual((r['resultat'], r['ticket']['code'], r['ticket']['type']), ('valide', 'PV-350', 'prevente'))

    def test_design_separe_par_type(self):
        d = self.client.get('/api/staff/billets-physiques/design?type=prevente', **STAFF).json()['design']
        self.assertEqual((d['bandeau'], d['prix']), ('PRÉVENTE', '2 500 FCFA'))
        self.post('/api/staff/billets-physiques/design?type=prevente', {'design': {'titre': 'DIP + DJ DANY'}}, **STAFF)
        jj = self.client.get('/api/staff/billets-physiques/design?type=jour_j', **STAFF).json()['design']
        self.assertEqual((jj['titre'], jj['bandeau']), ('Dip Doundou Guiss', 'JOUR J'))
        pv = self.client.get('/api/staff/billets-physiques/design?type=prevente', **STAFF).json()['design']
        self.assertEqual(pv['titre'], 'DIP + DJ DANY')

    def test_nombre_papier_prevente_borne(self):
        r = self.client.post('/api/staff/billets-physiques?type=prevente&nombre=900', **STAFF)
        self.assertEqual(r.status_code, 400)


def signer_webhook(corps, secret='whsec-test', t='1700000000'):
    import hashlib
    import hmac
    return f't={t},v1=' + hmac.new(secret.encode(), t.encode() + corps, hashlib.sha256).hexdigest()


@override_settings(STAFF_ACCESS_CODE='test-code', WAVE_API_KEY='wave-test', WAVE_WEBHOOK_SECRET='whsec-test',
                   PAIEMENT_SIMULE=False, SITE_URL='https://billeteriecjics.com')
class WaveCheckoutTest(TestCase):
    def setUp(self):
        from unittest import mock

        from django.core.cache import cache
        cache.clear()
        self.ev = generer_demo()
        self.sessions = {}

        def appel(url, corps=None):
            if corps is not None:
                sid = f'cos-{len(self.sessions) + 1}'
                self.sessions[sid] = {
                    'id': sid, 'amount': corps['amount'], 'currency': 'XOF', 'client_reference': corps['client_reference'],
                    'checkout_status': 'open', 'payment_status': 'processing', 'transaction_id': None,
                    'wave_launch_url': f'https://pay.wave.com/c/{sid}', 'success_url': corps['success_url'],
                }
                return self.sessions[sid]
            return self.sessions[url.rsplit('/', 1)[1]]

        patch = mock.patch('billetterie.wave._appel', side_effect=appel)
        patch.start()
        self.addCleanup(patch.stop)

    def creer(self):
        r = self.client.post('/api/paiements', json.dumps({'nom': 'Awa Ba', 'telephone': '771234567'}), content_type='application/json')
        self.assertEqual(r.status_code, 201)
        return r.json()['paiement']

    def payer_chez_wave(self, sid, montant=None, transaction='TCN4Y4ZC3FM'):
        s = self.sessions[sid]
        s.update(checkout_status='complete', payment_status='succeeded', transaction_id=transaction)
        if montant:
            s['amount'] = str(montant)
        return s

    def webhook(self, session, signature=None):
        corps = json.dumps({'id': 'AE_1', 'type': 'checkout.session.completed', 'data': session}).encode()
        return self.client.post('/api/wave/webhook', corps, content_type='application/json',
                                HTTP_WAVE_SIGNATURE=signature or signer_webhook(corps))

    def test_session_wave_creee_avec_le_paiement(self):
        p = self.creer()
        self.assertTrue(p['automatique'])
        self.assertEqual(p['wave_url'], 'https://pay.wave.com/c/cos-1')
        s = self.sessions['cos-1']
        self.assertEqual((s['amount'], s['client_reference']), ('2500', p['reference']))
        self.assertEqual(s['success_url'], f"https://billeteriecjics.com/paiement/{p['reference']}")
        self.assertIsNone(self.client.get('/api/evenement').json()['wave_url'])

    def test_webhook_emet_le_billet_automatiquement(self):
        ref = self.creer()['reference']
        self.assertEqual(self.webhook(self.payer_chez_wave('cos-1')).status_code, 200)
        p = self.client.get(f'/api/paiements/{ref}').json()['paiement']
        self.assertEqual(p['statut'], 'reussi')
        self.assertEqual(p['transaction_wave'], 'TCN4Y4ZC3FM')
        t = Ticket.objects.get(pk=p['ticket_id'])
        self.assertEqual((t.statut, t.acheteur_nom), ('vendu', 'Awa Ba'))
        # Notification rejouée : toujours un seul billet
        self.webhook(self.sessions['cos-1'])
        self.assertEqual(Ticket.objects.exclude(statut='disponible').count(), 1)

    def test_webhook_signature_invalide(self):
        self.creer()
        r = self.webhook(self.payer_chez_wave('cos-1'), signature='t=1700000000,v1=faux')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(Ticket.objects.exclude(statut='disponible').count(), 0)

    def test_montant_different_pas_de_billet(self):
        ref = self.creer()['reference']
        self.webhook(self.payer_chez_wave('cos-1', montant=100))
        self.assertIsNone(self.client.get(f'/api/paiements/{ref}').json()['paiement']['ticket_id'])

    def test_retour_de_wave_sans_webhook(self):
        # Le webhook n'est pas encore arrivé : la page de paiement relit la session Wave
        ref = self.creer()['reference']
        self.payer_chez_wave('cos-1')
        p = self.client.get(f'/api/paiements/{ref}').json()['paiement']
        self.assertEqual(p['statut'], 'reussi')
        self.assertIsNotNone(p['ticket_id'])

    def test_session_expiree(self):
        ref = self.creer()['reference']
        self.sessions['cos-1']['checkout_status'] = 'expired'
        self.assertEqual(self.client.get(f'/api/paiements/{ref}').json()['paiement']['statut'], 'echoue')

    def test_declaration_manuelle_refusee(self):
        ref = self.creer()['reference']
        r = self.client.post(f'/api/paiements/{ref}/declarer', '{}', content_type='application/json')
        self.assertEqual(r.status_code, 409)
