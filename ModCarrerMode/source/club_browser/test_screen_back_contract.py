"""Run the installed APTs with a non-literal navigation event identifier.

FIFA maps ESC and the controller's back button to InputCodes.BACK. The route
must also work in waiting views, before the mod has any career data to show.
"""
from pathlib import Path
import os
import unittest

from apt_vm import Object
from build_package import read_nav, walk
from native_review_vm import open_native

SCREENS = ('CareerRetirement', 'CareerClubTransfer', 'BankLoansV2', 'ClubFinance',
    'TransferMarket', 'TransferMarketLoading', 'ManagerMarket', 'MatchPreview',
    'MatchPreviewLoading', 'DressingRoom', 'DressingRoomPlayers', 'ClubBrowser',
    'CareerCompetitions', 'WorldClubRanking', 'WorldNationRanking')


class ScreenBackContract(unittest.TestCase):
    def test_all_installed_custom_views_send_the_mapped_back_event(self):
        game = Path(os.environ.get('SERVER16_GAME_ROOT', Path(__file__).resolve().parents[3]))
        for name in SCREENS:
            with self.subTest(screen=name):
                package = game/'data/ui/game/screens/career/server16'/(name.lower()+'.big')
                vm, view, _, calls = open_native(package,
                    full='game.screens.career.server16.'+name,
                    callbacks={'GetEvents': lambda owner, args: Object({'BACK': 42})})
                if view.get('Ready'):
                    vm.invoke(view.get('Ready'), view)
                before = len(vm.errors)
                calls.clear()
                vm.invoke(view.get('LocalEventHandler'), view, (1, True))
                if name=='CareerCompetitions':
                    # This view delegates Back to the verified native owner:
                    # it first closes an expanded bracket/round, or returns
                    # to the hub. It must not dispatch BACK twice from APT.
                    self.assertEqual([('SendSystemEvent',['Calendar','Server16ClubBrowser','comp_back'])],[(k,list(v)) for k,v in calls])
                else:
                    self.assertIn(('SendEvent', ['Calendar', 42, '']), [(k, list(v)) for k, v in calls])
                self.assertEqual([], vm.errors[before:])

    def test_every_custom_career_flow_can_return_to_the_hub(self):
        game = Path(os.environ.get('SERVER16_GAME_ROOT', Path(__file__).resolve().parents[3]))
        folder = game/'data/ui/nav/careermode'
        hub = read_nav((folder/'mainmenuhubflow.nav').read_text(encoding='utf-8-sig'))
        external = {node['file'].split('/')[-1].lower(): node
                    for node in walk(hub) if node.get('type') == 'external' and node.get('file')}
        flows = list(folder.glob('server16*flow.nav'))
        self.assertGreaterEqual(len(flows), 12)
        for path in flows:
            with self.subTest(flow=path.name):
                flow = read_nav(path.read_text(encoding='utf-8-sig'))
                owner = external[path.name.lower()]
                self.assertEqual(owner['outputs']['Back'], 'MainMenuHub')
                self.assertEqual(owner['outputs']['back'], 'MainMenuHub')
                for state in flow['states']:
                    if not any(action == 'loadView' for action, _ in state.get('onEnter', [])):
                        continue
                    for event in ('Back', 'back'):
                        # A roster opened inside the dressing room first goes
                        # back to the room. Follow that legitimate nested path
                        # instead of requiring every Back to leave it directly.
                        current, seen = state, set()
                        while True:
                            self.assertNotIn(current['name'], seen, 'Back route loops')
                            seen.add(current['name'])
                            transition = next(t for t in current['transitions'] if t['event'] == event)
                            self.assertEqual(1, len(transition['targets']))
                            target = transition['targets'][0]
                            if target == 'Back':
                                self.assertIn(['executeCMAction', ['ReturnToHubFromCalendar']], transition['actions'])
                                break
                            current = next(s for s in flow['states'] if s['name'] == target)


if __name__ == '__main__':
    unittest.main()
