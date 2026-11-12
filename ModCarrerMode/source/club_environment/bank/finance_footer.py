"""A scoped, spaced legend using FIFA's original HelpItem movie clips."""

SLOT_WIDTH = 240
FOOTER_Y = 1030
R = ('r', 1)
P = lambda obj, name: ('p', obj, name)
T = lambda name: P(R, name)
HELP = ('path', ('game', 'globalClasses', 'HelpManager'))
AND = lambda x, y: ('bin', 16, x, y)
EQ = lambda x, y: ('bin', 73, x, y)


def commands(scene):
    items = [('ADVANCE', 'Alterar' if scene['key'] == 'settings' else 'Selecionar'),
             ('BACK', 'Voltar'), ('L2R2', 'Abas'), ('LAS', 'Navegar')]
    if any(scene.get(k, scene['key']) != scene['key']
           for k in ('scrollPrevious', 'scrollNext')):
        items.append(('RAS_UD', 'Rolar lista'))
    return tuple(items)


def emit(a, scenes):
    import build_screen as b
    from native_screen import arr

    def context(a):
        # Group pages with the same legend instead of expanding the script
        # once per receipt/history page in a long career.
        groups = {}
        for index, scene in enumerate(scenes):
            groups.setdefault(commands(scene), []).append(index)
        for items, pages in groups.items():
            selected = False
            for page in pages:
                selected = ('bin', 17, selected, EQ(T('page'), page))
            a.when(selected, lambda a, items=items: a.ret(arr(
                b.call(b.path('ion', 'manager', 'HelpItem'),
                       'CreateHelpTickerItem', code, label)
                for code, label in items)))
        a.ret(arr(()))
    a.function('getHelpContext', 0, context)

    def refresh(a):
        a.when(T('financeHelpDelegate'), lambda a: None, lambda a:
               a.set(R, 'financeHelpDelegate', b.call(
                   b.path('cafe', 'utility', 'Delegate'), 'Create', R,
                   T('getHelpContext'))))
        a.do(HELP, 'SetCustomSource', T('financeHelpDelegate'))
        a.do(HELP, 'Update')
        a.do(HELP, 'Show')
        a.do(R, 'LayoutFinanceHelp')
    a.function('RefreshFinanceHelp', 0, refresh)

    def layout(a):
        # The global display is shared with the hub and modal screens. Never
        # move a different screen's footer, even during asynchronous loading.
        owned = AND(T('financeHelpDelegate'), EQ(
            P(HELP, 'm_cbCustomSource'), T('financeHelpDelegate')))
        a.when(AND(owned, ('not', T('exiting'))), lambda a: None,
               lambda a: a.ret())
        display = P(HELP, 'mcHelpDisplay')
        holder = P(display, 'mcHelpItemsHolder')
        a.when(holder, lambda a: None, lambda a: a.ret())
        def capture(a):
            a.set(R, 'financeHelpDisplay', display)
            a.set(R, 'financeHelpY', P(holder, '_y'))
            a.set(R, 'financeHelpScrollerY', P(P(display, 'mcTextScroller'), '_y'))
        a.when(EQ(T('financeHelpDisplay'), display), lambda a: None, capture)
        a.set(holder, '_y', FOOTER_Y)
        a.when(P(display, 'mcTextScroller'), lambda a:
               a.set(P(display, 'mcTextScroller'), '_y', FOOTER_Y))
        a.set(R, 'financeHelpSlot', 0)
        # Stock HelpDisplay/PanelHelpBar creates mcHelpItem + index. Keep its
        # actual icons, font, device mapping, and native input handling. Only
        # space the existing clips; never rebuild symbols on frame ticks.
        for index in range(8):
            clip = P(holder, 'mcHelpItem' + str(index))
            def place(a, clip=clip):
                a.set(clip, '_x', ('bin', 12, T('financeHelpSlot'), SLOT_WIDTH))
                icon_width = P(P(clip, 'mcIcon'), '_width')
                a.set(R, 'financeHelpLabelX', 76)
                valid = AND(('bin', 103, icon_width, 0), ('bin', 72, icon_width, 140))
                a.when(valid, lambda a: a.set(R, 'financeHelpLabelX',
                                            ('bin', 71, icon_width, 12)))
                for field in ('txtLabel', 'txtShadow'):
                    a.when(P(clip, field), lambda a, field=field:
                           a.set(P(clip, field), '_x', T('financeHelpLabelX')))
                a.set(R, 'financeHelpSlot', ('bin', 71, T('financeHelpSlot'), 1))
            a.when(AND(clip, P(clip, 'txtLabel')), place)
    a.function('LayoutFinanceHelp', 0, layout)

    def frame(a):
        a.when(T('exiting'), lambda a: a.ret())
        a.when(T('financePolling'), lambda a: a.do(R, 'Poll'))
        a.set(R, 'financeHelpFrames', ('bin', 71, T('financeHelpFrames'), 1))
        a.when(('bin', 72, T('financeHelpFrames'), 12), lambda a: a.ret())
        a.set(R, 'financeHelpFrames', 0)
        a.do(R, 'LayoutFinanceHelp')
    a.function('FinanceFrame', 0, frame)


def release(a):
    owned = AND(T('financeHelpDelegate'), EQ(
        P(HELP, 'm_cbCustomSource'), T('financeHelpDelegate')))
    def reset(a):
        display = T('financeHelpDisplay')
        def restore(a):
            a.set(P(display, 'mcHelpItemsHolder'), '_y', T('financeHelpY'))
            a.when(P(display, 'mcTextScroller'), lambda a:
                   a.set(P(display, 'mcTextScroller'), '_y', T('financeHelpScrollerY')))
        a.when(display, restore)
        a.do(HELP, 'SetCustomSource', None)
        a.do(HELP, 'Clear')
    a.when(owned, reset)
    a.set(R, 'financeHelpDelegate', None)
    a.set(R, 'financeHelpDisplay', None)
