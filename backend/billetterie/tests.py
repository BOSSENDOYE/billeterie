import json
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
        self.assertEqual((stats['vendus'], stats['scannes'], stats['restants']), (1, 1, 599))
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
        tarif = self.client.get('/api/evenement').json()['tarif']
        self.assertEqual((tarif['type'], tarif['prix'], tarif['restants']), ('prevente', 2500, 400))
        ticket = self.client.get(f'/api/tickets/{self.acheter()}').json()['ticket']
        self.assertEqual((ticket['type'], ticket['prix'], ticket['code']), ('prevente', 2500, 'PV-001/400'))

    def test_jour_j_apres_la_date(self):
        self.passer_au_jour_j()
        p = self.creer()
        self.assertEqual((p['type'], p['montant']), ('jour_j', 3000))
        self.assertIn('amount=3000', p['wave_url'])
        ticket = self.client.get(f'/api/tickets/{self.acheter()}').json()['ticket']
        self.assertEqual((ticket['type'], ticket['code']), ('jour_j', 'JJ-001/200'))

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
        self.assertEqual((t['type'], t['statut'], t['code']), ('jour_j', 'utilise', 'JJ-001/200'))
        # Le billet ne peut pas resservir
        self.assertEqual(self.post('/api/staff/scan', {'qr': t['qr']}, **STAFF).json()['resultat'], 'utilise')
        stats = self.client.get('/api/staff/stats', **STAFF).json()['stats']
        self.assertEqual(stats['par_type']['jour_j']['recette'], 3000)

    def test_vente_guichet_reservee_au_personnel(self):
        self.assertEqual(self.post('/api/staff/vente-guichet', {'type': 'jour_j'}).status_code, 401)
