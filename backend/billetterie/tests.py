import json

from django.test import TestCase, override_settings

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
        self.assertEqual((stats['vendus'], stats['scannes'], stats['restants']), (1, 1, 299))

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
