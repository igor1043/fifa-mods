"""Confirmation copy must fit its real native edit-text bounds and stay usable."""
import unittest
from PIL import ImageFont
from formats import AptFile, BigFile, Placement
from loans import borrow, empty, presentation
from test_finance_live_ui import open_screen, text
import bank_ui_r60 as ui


class ConfirmationLayoutTests(unittest.TestCase):
    def view(self, action):
        state, budget, _ = borrow(empty(1043,20260108), request_id='approved',
            club=1043, today=20260108, budget=28_000_000, bank=9, amount=3_000_000, months=12)
        return presentation(state,20260108,budget,ready=True,nonce='CONFIRM',
            club_name='Flamengo',wage_budget=190_000,
            result=dict(sequence=3,action=action,ok=True,kind='loan_decision' if action==0 else 'payment',
                message='Crédito aplicado. Salve a carreira no FIFA. O e-mail de aprovação está na fila da caixa de mensagens.'))

    def test_approval_and_payment_copy_fit_and_keep_the_native_help_and_statement_action(self):
        for action in (0,1,2):
            with self.subTest(action=action):
                view=self.view(action)
                vm, screen, _=open_screen(view)
                vm.global_.set('Server16BankPendingSequence',3)
                screen.set('page',5)
                vm.invoke(screen.get('Refresh'),screen)
                self.assertEqual(text(screen,'detail0'),
                    'Empréstimo aprovado. Crédito disponível.' if action==0 else 'Pagamento confirmado no orçamento.')
                self.assertEqual(text(screen,'detail1'),'Confira a confirmação na caixa de mensagens.')
                self.assertIn('31.000.000',text(screen,'detail2'))
                self.assertIn('3.458.735',text(screen,'detail4'))
                self.assertIn('08/02/2026',text(screen,'detail6'))
                self.assertEqual(sum('Salve a carreira' in text(screen,f'detail{i}') for i in range(11)),1)
                apt=AptFile(BigFile(ui.b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big'))
                fields={p.name:(p,apt.characters[p.character]) for p in apt.characters[9].frames[0]
                    if isinstance(p,Placement) and p.name and p.character in apt.characters and apt.characters[p.character].type==2}
                previous_bottom=None
                # Check the actual emitted native rectangles, not a separate mock layout.
                for i in (0,1,2,4,6,8):
                    name=f'detail{i}'
                    placement,char=fields[name]
                    left,top,right,bottom=char.bounds
                    x=screen.get(name).get('_x')
                    y=screen.get(name).get('_y')
                    x=placement.matrix[4] if x is None else x
                    y=placement.matrix[5] if y is None else y
                    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',round(char.font_size))
                    self.assertLessEqual(font.getlength(text(screen,name)),right-left-24,name)
                    self.assertGreaterEqual(x,930,name)
                    self.assertLessEqual(x+right,1770,name)
                    self.assertLessEqual(y+bottom,850,name)
                    if previous_bottom is not None:self.assertGreaterEqual(y+top,previous_bottom,name)
                    previous_bottom=y+bottom
                self.assertEqual(vm.invoke(screen.get('getHelpContext'),screen),
                    [('ADVANCE','Selecionar'),('BACK','Voltar')])
                vm.invoke(screen.get('Select'),screen)
                self.assertEqual(screen.get('page'),3)
                self.assertEqual(text(screen,'cell1_0'),'01 / 12')
                self.assertIsNone(vm.global_.get('Server16BankRequestV2'))


if __name__=='__main__':
    unittest.main()
