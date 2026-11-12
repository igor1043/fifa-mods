"""Exercise the built APT against native-style data-provider payloads."""
from pathlib import Path
import argparse
import json
import struct
import build


def verify(path, studio):
    build.dependencies(studio)
    from formats import AptFile, BigFile, Placement, Reader
    from apt_actions import Actions
    from apt_test_vm import NativeVM
    from apt_vm import Native, Object, Function

    apt = AptFile(BigFile(path))
    actions = Actions(apt).read_all()
    assert not actions.errors
    apt.validate_layout()
    # The generic decoder preserves raw bytes as Latin-1. FIFA's native text
    # path interprets the UTF-8 string operands emitted by our screen builder.
    def native_strings(code):
        for instruction in code:
            if isinstance(instruction.value, str):
                try:
                    instruction.value = instruction.value.encode('latin1').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            if instruction.body:
                native_strings(instruction.body)
    for code in actions.cache.values():
        native_strings(code)
    calls = []
    vm = None

    def native(name, owner, args):
        calls.append((name, owner, tuple(args)))
        if name == 'original.SetData':
            data = owner.get('m_objData')
            owner.get('txtTeam').set('text', data.get('TEAM_NAME'))
            owner.get('txtName').set('text', data.get('NAME'))
            owner.get('mcMiddle').set('_width', 230)
            vm.invoke(owner.get('__careerDrawCoachGraph'), owner)
        elif name == 'original.Publish':
            owner.set('m_objData', args[0].get('data')[0])
            vm.invoke(owner.get('SetData'), owner)
        elif name == 'createEmptyMovieClip':
            clip = Object({'_x': 0, '_y': 0, '_visible': True, 'drawing': []})
            owner.set(args[0], clip)
            return clip
        elif name == 'createTextField':
            owner.set(args[0], Object(dict(zip(('_x', '_y', '_width', '_height'), args[2:]))))
        elif name in ('setTextFormat', 'setNewTextFormat'):
            owner.set('format', args[0])
        elif name == 'clear':
            owner.set('drawing', [])
        elif name in ('lineStyle', 'beginFill', 'moveTo', 'lineTo', 'endFill'):
            owner.get('drawing').append((name, list(args)))
        elif name == 'LocalizeCurrencyWithType':
            return f'{int(args[1]):,}'.replace(',', '.')

    class HeaderVM(NativeVM):
        def method(self, obj, name, args):
            if name == 'call' and isinstance(obj, (Function, Native)):
                return self.invoke(obj, args[0], args[1:])
            return super().method(obj, name, args)

    vm = HeaderVM(native)
    # Match FIFA's restricted native APT environment. The generic test VM
    # supplies a global Number constructor which the real header cannot rely
    # on; leaving it enabled concealed the undefined%/zero-cash regression.
    vm.global_.set('Number', None)
    for code in actions.cache.values():
        if code[0].op == 136:
            vm.run(code, vm.global_, vm.global_)
    proto = vm.path('.'.join(build.PROTO))
    assert proto and proto.get(build.MARKER)
    methods = tuple(proto.get(name) for name in ('SetData', 'Publish', 'Shutdown'))
    for code in actions.cache.values():
        if code[0].op == 136:
            vm.run(code, vm.global_, vm.global_)
    assert methods == tuple(proto.get(name) for name in ('SetData', 'Publish', 'Shutdown'))
    for name in ('SetData', 'Publish', 'Shutdown'):
        proto.set(build.OLD + name, Native('original.' + name))
    vm.path('game').set('uif', Object({'UIFDataProviderList': Object(), 'UIFUtility': Object()}))
    vm.path('game.uif.UIFDataProviderList').set('CM_STATISTICS_DP', 900)
    vm.path('game.uif.UIFDataProviderList').set('CM_STANDINGS_DP', 700)
    vm.path('game.uif.UIFUtility').set('RegisterDataProvider', Native('RegisterDataProvider'))
    vm.path('game.uif.UIFUtility').set('UnregisterDataProvider', Native('UnregisterDataProvider'))
    vm.global_.set('ION_Localization', Object({'LocalizeCurrencyWithType': Native('LocalizeCurrencyWithType')}))

    data = Object({'ASSET_ID': 112893, 'TEAM_NAME': 'Inter Miami', 'NAME': 'Senhor Manager', 'IS_TOURNAMENTMODE': '0'})
    header = Object({'m_objData': data}, prototype=proto)
    for name, x, y, width, height in (
        ('mcHeaderLeft', 0, 0, 32, 79), ('mcMiddle', 32, 0, 378, 79),
        ('mcRight', 410, 0, 88, 79), ('mcCrest', 15, 5, 70, 70),
        ('txtTeam', 97, 5, 300, 30), ('txtName', 97, 37, 300, 30)):
        header.set(name, Object({'_x': x, '_y': y, '_width': width, '_height': height}))
    header.set('__careerCoachGraph', Object({'_visible': True}))
    icons = ('mcHeaderEfficiencyIcon', 'mcHeaderPrestigeIcon', 'mcHeaderMetricDivider',
             'mcHeaderBoardIcon', 'mcHeaderBoardDivider', 'mcHeaderBoardTrack', 'mcHeaderBoardFill') + build.RIGHT_ICONS
    for name in icons:
        header.set(name, Object())
    for name in build.RIGHT_PARTS:
        header.set(name, Object())
    header.set(build.branding.LOGO, Object({'_visible': True}))

    def invoke(name, *args):
        return vm.invoke(header.get(name), header, args)

    def publish(club, efficiency, prestige, confidence=86, date='30/12/2026', days=2, cash=94661315, currency=0, manager=1):
        rows = [Object({'ID': 'UNRELATED_TILE', 'PARAM': 'ignore'}),
                Object({'ID': 'CAREER_HEADER_EFFICIENCY', 'PARAM': '99%'})]
        rows.extend(Object({'ID': key, 'PARAM': value}) for key, value in (
            ('CAREER_HEADER_CLUB_ID', club), ('COACH_EFFICIENCY', efficiency),
            ('CAREER_HEADER_PRESTIGE', prestige), ('CAREER_HEADER_BOARD_CONFIDENCE', confidence),
            ('CAREER_HEADER_DATE', date), ('CAREER_HEADER_MARKET_DAYS', days),
            ('CAREER_HEADER_CASH', cash), ('CAREER_HEADER_CURRENCY', currency), ('CAREER_HEADER_MANAGER', manager)))
        invoke('Publish', Object({'data': rows}), 900)

    # Exercise the real legacy wrapper too. The stock API has two arguments,
    # as seen in the native CM_HUB_WIDGET_DP constructor/shutdown calls.
    invoke('InitComponents')
    assert [(args[0], args[1]) for name, _, args in calls if name == 'RegisterDataProvider'] == [(header, 700)]
    assert all(len(args) == 2 for name, _, args in calls if name == 'RegisterDataProvider')
    invoke('SetData')
    clip = header.get('__careerHeaderMetrics')
    assert clip.get('effValue').get('text') == '—'
    assert clip.get('boardValue').get('text') == '—'
    right = header.get('__careerRightMetrics')
    assert right.get('dateValue').get('text') == right.get('marketValue').get('text') == right.get('cashValue').get('text') == '—'
    assert header.get('mcHeaderBoardFill').get('_visible') is False
    assert header.get('__careerCoachGraph').get('_visible') is False
    assert header.get('txtTeam').get('text') == 'Inter Miami'
    assert header.get('txtName').get('text') == 'Senhor Manager'
    invoke('SetData')
    registered = [args for name, _, args in calls if name == 'RegisterDataProvider']
    assert registered == [(header, 700), (header, 900)]
    publish(112893, '45%', '4,3/5')
    assert clip.get('effValue').get('text') == '45%'
    assert clip.get('prestigeValue').get('text') == '4,3/5'
    assert clip.get('boardValue').get('text') == '86%'
    assert clip.get('boardLabel').get('text') == 'Av. Diretoria'
    assert header.get('mcHeaderBoardFill').get('_visible') is False
    assert clip.get('boardLabel').get('_x') + clip.get('boardLabel').get('_width') <= clip.get('boardValue').get('_x')
    assert clip.get('boardValue').get('_x') + clip.get('boardValue').get('_width') <= build.ROW_WIDTH
    assert right.get('dateValue').get('text') == '30/12/2026'
    assert right.get('marketValue').get('text') == 'Abre em 2 dias'
    assert right.get('cashValue').get('text') == 'R$ 94.661.315'
    assert all(right.get(name).get('format').get('size') == 12 for name in ('dateLabel', 'marketLabel', 'cashLabel'))
    assert right.get('dateValue').get('format').get('size') == right.get('cashValue').get('format').get('size') == 18
    assert right.get('marketValue').get('format').get('size') == 17
    assert right.get('dateValue').get('_x') >= 64
    assert clip.get('boardLabel').get('_x') < clip.get('prestigeLabel').get('_x')
    for icon,label in zip(build.RIGHT_ICONS[:3],('dateLabel','marketLabel','cashLabel')):
        assert header.get(icon).get('_y') == right.get(label).get('_y') + 2
        assert header.get(icon).get('_height') == 18
    for (key,x,width,fallback),icon in zip(build.RIGHT_COLUMNS,build.RIGHT_ICONS[:3]):
        value=right.get(key+'Value');label=right.get(key+'Label')
        assert value.get('format').get('align') == 'center'
        assert value.get('_x') + value.get('_width')/2 == x + width/2
        group_left=header.get(icon).get('_x') - build.RIGHT_X
        assert abs(group_left + (26+fallback)/2 - (x+width/2)) < .001
        assert label.get('_x') == group_left+26
        assert label.get('_x') + label.get('_width') <= x+width
    # Native TextField measurements center the complete title/icon group.
    # A runtime without textWidth retains the bounded fallback above.
    right.get('marketLabel').set('textWidth',120)
    invoke('__careerDrawCoachGraph')
    market_column=build.RIGHT_COLUMNS[1]
    assert abs(header.get(build.RIGHT_ICONS[1]).get('_x')-build.RIGHT_X+(26+120)/2-(market_column[1]+market_column[2]/2)) < .001
    right.get('marketLabel').set('textWidth',None)
    # Wide stock text fields must not recreate the empty space after Prestige.
    header.get('txtTeam').set('_width',1800);header.get('txtName').set('_width',1600)
    invoke('__careerDrawCoachGraph')
    assert header.get('mcRight').get('_x') == clip.get('_x')+build.ROW_WIDTH+12
    assert header.get('mcRight').get('_x')+88 < 800
    assert header.get(build.branding.LOGO).get('_visible') is False
    assert right.get('_x') == build.RIGHT_X and right.get('_visible') is True
    assert header.get('mcRight').get('_x') + 88 < build.RIGHT_X
    assert build.RIGHT_X + build.RIGHT_WIDTH == build.RIGHT_EDGE
    for label, value in (('dateLabel', 'dateValue'), ('marketLabel', 'marketValue'), ('cashLabel', 'cashValue')):
        assert right.get(label).get('_y') + right.get(label).get('_height') <= right.get(value).get('_y') + 1
        assert right.get(value).get('_x') + right.get(value).get('_width') <= build.RIGHT_WIDTH
    assert clip.get('effLabel').get('_y') == clip.get('prestigeLabel').get('_y') == 4
    assert clip.get('effValue').get('_y') == clip.get('prestigeValue').get('_y') == 0
    assert 'UNRELATED_TILE' not in header.get('__careerHeaderData').values
    # Native statistics can contain thousands of unrelated rows. Once our
    # trailing fields arrive, the header stops scanning the shared payload.
    unrelated = [Object({'ID': 'OTHER_' + str(index), 'PARAM': index}) for index in range(5000)]
    rows = [Object({'ID': key, 'PARAM': value}) for key, value in (
        ('CAREER_HEADER_CLUB_ID', 112893), ('COACH_EFFICIENCY', '45%'),
        ('CAREER_HEADER_PRESTIGE', '4,3/5'), ('CAREER_HEADER_BOARD_CONFIDENCE', 86),
        ('CAREER_HEADER_DATE', '30/12/2026'), ('CAREER_HEADER_MARKET_DAYS', 2),
        ('CAREER_HEADER_CASH', 94661315), ('CAREER_HEADER_CURRENCY', 0), ('CAREER_HEADER_MANAGER', 1))]
    before = vm.steps
    invoke('Publish', Object({'data': unrelated + rows}), 900)
    assert vm.steps - before < 6000
    assert clip.get('boardValue').get('text') == '86%'
    # Real career report: one win, two draws, one defeat. The native History
    # tile publishes 25% while points efficiency would be 41%. Share its field.
    publish(112893, '25%', '3,0/5')
    assert clip.get('effValue').get('text') == '25%'
    assert all(header.get(name).get('_height') == build.HEIGHT for name in ('mcHeaderLeft', 'mcMiddle', 'mcRight'))
    assert header.get('mcCrest').get('_y') == 5 + (build.HEIGHT - 79) / 2
    # A crest loaded asynchronously must stay centered even while its loader
    # reports height zero. This reproduces the observed downward displacement.
    header.get('mcCrest').set('_height', 0)
    invoke('__careerDrawCoachGraph')
    assert header.get('mcCrest').get('_y') == 5 + (build.HEIGHT - 79) / 2
    assert clip.get('_x') + build.ROW_WIDTH < header.get('mcRight').get('_x')
    snapshot = {'texts': {name: dict(clip.get(name).values) for name in ('effLabel', 'effValue', 'prestigeLabel', 'prestigeValue', 'boardLabel', 'boardValue')},
                'drawing': clip.get('drawing'), 'x': clip.get('_x'), 'y': clip.get('_y'),
                'right_x': header.get('mcRight').get('_x')}
    for field in snapshot['texts'].values():
        field['format'] = dict(field['format'].values)
    publish(1043, '100%', '5,0/5')
    assert clip.get('effValue').get('text') == '—'
    assert clip.get('boardValue').get('text') == '—' and header.get('mcHeaderBoardFill').get('_visible') is False
    assert right.get('cashValue').get('text') == right.get('dateValue').get('text') == '—'
    invoke('Publish', Object({'data': [Object({'ASSET_ID': 1043, 'TEAM_NAME': 'Flamengo', 'NAME': 'Outro Manager', 'IS_TOURNAMENTMODE': '0'})]}), 901)
    assert header.get('__careerHeaderData') is None
    assert header.get('txtTeam').get('text') == 'Flamengo'
    publish(1043, '', '', -1)
    assert clip.get('effValue').get('text') == clip.get('prestigeValue').get('text') == clip.get('boardValue').get('text') == '—'
    publish(1043, '0%', '3,0/5')
    assert clip.get('effValue').get('text') == '0%'
    for rating in (0, 1, 24, 59, 86, 100):
        publish(1043, '0%', '3,0/5', rating)
        assert clip.get('boardValue').get('text') == str(rating) + '%'
        assert header.get('mcHeaderBoardFill').get('_visible') is False
    for rating in (-1, 101, 999):
        publish(1043, '0%', '3,0/5', rating)
        assert clip.get('boardValue').get('text') == '—'
        assert header.get('mcHeaderBoardFill').get('_visible') is False
    invoke('Publish', Object({'data': [Object({'ID': key, 'PARAM': value}) for key, value in (
        ('CAREER_HEADER_CLUB_ID', 1043), ('COACH_EFFICIENCY', '0%'), ('CAREER_HEADER_PRESTIGE', '3,0/5'))]}), 900)
    assert clip.get('boardValue').get('text') == '—'
    assert header.get('mcHeaderBoardFill').get('_visible') is False
    for days, text in ((0, 'Mercado aberto'), (1, 'Abre amanhã'), (2, 'Abre em 2 dias'), (122, 'Abre em 122 dias'), (-1, '—')):
        publish(1043, '0%', '3,0/5', days=days, cash=0, currency=2)
        assert right.get('marketValue').get('text') == text
        assert right.get('cashValue').get('text') == '€ 0'
    publish(1043, '0%', '3,0/5', date='01/01/2027', cash=111, currency=1)
    assert right.get('dateValue').get('text') == '01/01/2027' and right.get('cashValue').get('text') == 'US$ 111'
    publish(1043, '0%', '3,0/5', cash=111, currency=3)
    assert right.get('cashValue').get('text') == '—'
    # Captured career example: user 0, Flamengo, Jan 2027. Exercise the same
    # actual values as both native integer fields and serialized PARAM text.
    publish(1043, '0%', '4,3/5', confidence=100, date='07/01/2027', days=0, cash=66020090, currency=0)
    assert clip.get('boardValue').get('text') == '100%'
    assert right.get('marketValue').get('text') == 'Mercado aberto'
    assert right.get('cashValue').get('text') == 'R$ 66.020.090'
    publish('1043', '0%', '4,3/5', confidence='100', date='07/01/2027', days='0', cash='66020090', currency='0', manager='1')
    assert clip.get('boardValue').get('text') == '100%'
    assert right.get('marketValue').get('text') == 'Mercado aberto'
    assert right.get('cashValue').get('text') == 'R$ 66.020.090'
    publish(1043, '0%', '3,0/5', manager=0)
    assert right.get('_visible') is False and header.get(build.branding.LOGO).get('_visible') is True
    assert all(header.get(name).get('_visible') is False for name in build.RIGHT_PARTS + build.RIGHT_ICONS)
    assert clip.get('boardLabel').get('_visible') is False
    publish(1043, '0%', '3,0/5')
    assert right.get('_visible') is True and clip.get('boardLabel').get('_visible') is True
    header.get('m_objData').set('IS_TOURNAMENTMODE', '1')
    invoke('SetData')
    assert clip.get('_visible') is False and header.get('mcMiddle').get('_height') == 79
    assert all(header.get(name).get('_visible') is False for name in icons)
    assert right.get('_visible') is False and all(header.get(name).get('_visible') is False for name in build.RIGHT_PARTS)
    invoke('Shutdown'); invoke('Shutdown')
    assert len([name for name, _, _ in calls if name == 'UnregisterDataProvider']) == 1
    assert header.get('__careerHeaderData') is None

    # Native relocation dereferences even anonymous Function2 name/parameter pointers.
    for code in actions.cache.values():
        for instruction in code:
            if instruction.op != 142:
                continue
            reader = Reader(apt.data, instruction.offset + 1, 8)
            name_pointer = reader.ptr()
            assert 0 < name_pointer < len(apt.data)
            reader.string(name_pointer)
            reader.pos = (reader.pos + 3) // 4 * 4
            count = reader.i(); reader.read('h'); reader.read('H')
            parameters = reader.ptr()
            assert 0 < parameters and parameters + count * 16 <= len(apt.data)
            assert all(item.op != 0 for item in instruction.body)
    component = next(character for character in apt.characters.values()
                     if character.type == 5 and any(isinstance(p, Placement) and p.name == 'txtTeam' for frame in character.frames for p in frame))
    left = next(p for p in component.frames[0] if isinstance(p, Placement) and p.name == 'mcHeaderLeft')
    assert apt.characters[left.character].type == 5
    for name in icons:
        placement = next(p for p in component.frames[0] if isinstance(p, Placement) and p.name == name)
        symbol = apt.characters[placement.character]
        assert symbol.type == 5
        child = next(p for p in symbol.frames[0] if isinstance(p, Placement))
        assert apt.characters[child.character].type == 1
        geo = apt.big.entries[str(child.character + 1)].data
        declared_triangles = struct.unpack_from('<I', geo, 88)[0]
        assert declared_triangles == (len(geo) - 96) // 96, 'Native triangle count truncates the icon in FIFA'
        assert declared_triangles > 0
        vertices = [struct.unpack_from('<2f', geo, offset) for offset in range(96, len(geo), 32)]
        assert len(vertices) == declared_triangles * 3
        assert max(x for x, _ in vertices) > min(x for x, _ in vertices)
        assert max(y for _, y in vertices) > min(y for _, y in vertices)
    for name, mirror in zip(build.RIGHT_PARTS, (-1, 1, -1)):
        placement = next(p for p in component.frames[0] if isinstance(p, Placement) and p.name == name)
        assert placement.matrix[0] == mirror
    assert not vm.errors
    assert not any(name == 'Number' for name, _, _ in calls)
    output = Path(path).parent / 'verification.json'
    output.write_text(json.dumps({'passed': True, 'steps': vm.steps, 'preview': snapshot}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS career hubs APT: centered title/icon groups and values, bounded compact left card, currencies, dates/windows, context transitions and native relocation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--studio', type=Path, required=True)
    args = parser.parse_args()
    verify(args.input, args.studio)
