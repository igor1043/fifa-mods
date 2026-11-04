"""Move the original FIFA help display only for the roster content area."""
FOOTER_Y = 1030  # Native 1920 x 1080 APT coordinates; cards end at 971.
R = ('r', 1)
HELP = ('path', ('game', 'globalClasses', 'HelpManager'))
P = lambda owner, name: ('p', owner, name)
T = lambda name: P(R, name)


def apply(a):
    display = P(HELP, 'mcHelpDisplay')
    holder = P(display, 'mcHelpItemsHolder')
    def place(a):
        def capture(a):
            a.set(R, 'marketFooterDisplay', display)
            a.set(R, 'marketFooterY', P(holder, '_y'))
            a.set(R, 'marketScrollerY', P(P(display, 'mcTextScroller'), '_y'))
            a.set(R, 'marketFooterCaptured', True)
        a.when(T('marketFooterCaptured'), lambda a: None, capture)
        a.set(holder, '_y', FOOTER_Y)
        a.set(P(display, 'mcTextScroller'), '_y', FOOTER_Y)
    a.when(holder, place)


def restore(a):
    def reset(a):
        a.set(P(T('marketFooterDisplay'), 'mcHelpItemsHolder'), '_y', T('marketFooterY'))
        a.set(P(T('marketFooterDisplay'), 'mcTextScroller'), '_y', T('marketScrollerY'))
        a.set(R, 'marketFooterCaptured', False)
    a.when(T('marketFooterCaptured'), reset)
