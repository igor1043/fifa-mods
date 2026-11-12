"""Exercise the native ticker with overlapping and asynchronously loaded clips."""
import unittest
from apt_vm import Object
import finance_ui as ui
import finance_footer as footer
from test_club_finance_ui import open_finance, view


class FinanceFooterTests(unittest.TestCase):
    def attach_display(self, vm, widths=(30, 30, 82, 38, 38)):
        manager = vm.path('game.globalClasses.HelpManager')
        clips = [Object({'_x': 0, '_y': 0, 'mcIcon': Object({'_width': width}),
                         'txtLabel': Object({'_x': 0}), 'txtShadow': Object({'_x': 0})})
                 for width in widths]
        holder = Object({'_y': 950, **{'mcHelpItem' + str(i): clip for i, clip in enumerate(clips)}})
        scroller = Object({'_y': 955})
        display = Object({'mcHelpItemsHolder': holder, 'mcTextScroller': scroller})
        manager.set('mcHelpDisplay', display)
        return manager, holder, scroller, clips

    def test_native_icons_and_captions_have_separate_slots_below_the_card(self):
        vm, screen, _ = open_finance(view())
        manager, holder, scroller, clips = self.attach_display(vm)
        vm.invoke(screen.get('LayoutFinanceHelp'), screen)
        self.assertEqual([c.get('_x') for c in clips], [0, 240, 480, 720, 960])
        self.assertEqual([c.get('txtLabel').get('_x') for c in clips], [42, 42, 94, 50, 50])
        self.assertEqual(holder.get('_y'), footer.FOOTER_Y)
        self.assertEqual(scroller.get('_y'), footer.FOOTER_Y)
        self.assertIs(clips[0].get('mcIcon'), holder.get('mcHelpItem0').get('mcIcon'))
        self.assertEqual(vm.errors, [])

    def test_legend_tracks_settings_and_only_scrollable_pages_show_right_stick(self):
        payload = view()
        payload['months'] = [dict(month=202601 + i) for i in range(12)]
        vm, screen, _ = open_finance(payload)
        scenes = ui.scenes(payload)
        for i, scene in enumerate(scenes):
            vm.invoke(screen.get('Go'), screen, [i])
            items = vm.invoke(screen.get('getHelpContext'), screen)
            self.assertIn(('L2R2', 'Abas'), items)
            self.assertIn(('LAS', 'Navegar'), items)
            scrollable = any(scene[k] != scene['key'] for k in ('scrollPrevious', 'scrollNext'))
            self.assertEqual(('RAS_UD', 'Rolar lista') in items, scrollable)
            self.assertIn(('ADVANCE', 'Alterar' if scene['key'] == 'settings' else 'Selecionar'), items)

    def test_delayed_native_clips_are_spaced_without_rebuilding_the_screen(self):
        vm, screen, calls = open_finance(view())
        manager, holder, scroller, clips = self.attach_display(vm, (0, 0, 0, 0))
        for _ in range(12):vm.invoke(screen.get('FinanceFrame'), screen)
        self.assertEqual([c.get('_x') for c in clips], [0, 240, 480, 720])
        self.assertTrue(all(c.get('txtLabel').get('_x') == 76 for c in clips))
        updates = sum(n == 'Update' for n, _ in calls)
        clips[2].get('mcIcon').set('_width', 82)
        for _ in range(12):vm.invoke(screen.get('FinanceFrame'), screen)
        self.assertEqual(clips[2].get('txtLabel').get('_x'), 94)
        self.assertEqual(sum(n == 'Update' for n, _ in calls), updates)
        self.assertFalse(any(n == 'SendSystemEvent' and a[1] == 'Server16SubmitBank' for n, a in calls))

    def test_exit_restores_shared_position_and_releases_its_delegate(self):
        vm, screen, calls = open_finance(view())
        manager, holder, scroller, _ = self.attach_display(vm)
        vm.invoke(screen.get('LayoutFinanceHelp'), screen)
        vm.invoke(screen.get('OnExitScreen'), screen)
        self.assertEqual((holder.get('_y'), scroller.get('_y')), (950, 955))
        self.assertIsNone(manager.get('m_cbCustomSource'))
        self.assertIsNone(screen.get('onEnterFrame'))
        self.assertTrue(any(n == 'Clear' for n, _ in calls))

    def test_does_not_move_or_clear_another_screens_footer(self):
        vm, screen, calls = open_finance(view())
        manager, holder, scroller, clips = self.attach_display(vm)
        other = Object()
        manager.set('m_cbCustomSource', other)
        vm.invoke(screen.get('LayoutFinanceHelp'), screen)
        self.assertEqual([c.get('_x') for c in clips], [0] * 5)
        before = len(calls)
        vm.invoke(screen.get('OnExitScreen'), screen)
        self.assertIs(manager.get('m_cbCustomSource'), other)
        self.assertFalse(any(n == 'Clear' for n, _ in calls[before:]))

    def test_timeout_stops_polling_but_keeps_the_footer_alive(self):
        payload = view();payload.update(ready=False, nonce='DISABLED')
        vm, screen, _ = open_finance(payload)
        screen.set('pollFrames', 1799)
        vm.invoke(screen.get('FinanceFrame'), screen)
        self.assertFalse(screen.get('financePolling'))
        self.assertIs(screen.get('onEnterFrame'), screen.get('FinanceFrame'))


if __name__ == '__main__':unittest.main()
