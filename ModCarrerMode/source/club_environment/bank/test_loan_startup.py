"""Guard native startup resources, beyond an unbounded offline functional VM."""
import inspect,sys,unittest
from apt_vm import VM
from loans import empty,presentation,quote
from bank_design import ORDER
from test_finance_live_ui import open_screen,text


class NativeStartupTests(unittest.TestCase):
    def bounded(self,callback):
        code=VM.run.__code__;lines,start=inspect.getsourcelines(VM.run)
        observed_line=next(start+i for i,line in enumerate(lines) if 'self.steps+=1' in line)
        metrics=dict(peak_stack=0,steps=0)
        def trace(frame,event,arg):
            if frame.f_code!=code:return None
            if event=='line' and frame.f_lineno==observed_line:
                used=len(frame.f_locals.get('stack',[]))
                metrics['peak_stack']=max(metrics['peak_stack'],used);metrics['steps']+=1
                if used>128:raise AssertionError('Native-screen operand stack exceeds the conservative budget: '+str(used))
            return trace
        previous=sys.gettrace();sys.settrace(trace)
        try:result=callback()
        finally:sys.settrace(previous)
        return result,metrics

    def test_first_open_never_materializes_all_bank_simulations_or_uses_a_large_operand_stack(self):
        view=presentation(empty(1043,20260211),20260211,31_356_816,ready=True,nonce='STARTUP')
        (vm,screen,_),metrics=self.bounded(lambda:open_screen(view))
        self.assertEqual(text(screen,'title'),'EMPRÉSTIMOS DO CLUBE')
        self.assertEqual(screen.get('page'),0)
        self.assertIsNone(screen.get('simulationPlan'))
        # Performance target, not an assertion about FIFA's instruction limit.
        # The eager catalog constructor used more than 64,000 evaluated steps.
        self.assertLess(metrics['steps'],25_000)
        self.assertLessEqual(metrics['peak_stack'],128)
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

    def test_48_month_plan_is_materialized_only_on_request_with_bounded_stack(self):
        view=presentation(empty(1043,20260211),20260211,31_356_816,ready=True,nonce='LAZY_PLAN')
        vm,screen,_=open_screen(view)
        screen.set('page',1);screen.set('focus',ORDER.index(10));screen.set('amountIndex',8);screen.set('termIndex',4)
        vm.invoke(screen.get('Refresh'),screen)
        self.assertIsNone(screen.get('simulationPlan'))
        screen.set('page',6)
        _,metrics=self.bounded(lambda:vm.invoke(screen.get('Refresh'),screen))
        plan=screen.get('simulationPlan')
        self.assertEqual(len(plan),48)
        self.assertEqual(plan[-1][0],'48')
        self.assertIn('2030',plan[-1][1])
        self.assertLessEqual(metrics['peak_stack'],128)
        self.assertEqual(text(screen,'cell1_2'),format(quote(10,100_000_000,48)['payments'][0]['amount'],',').replace(',','.'))
        self.assertIsNone(vm.global_.get('Server16BankRequestV2'))


if __name__=='__main__':unittest.main()
