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
            a.set(R, 'rosterFooterDisplay', display)
            a.set(R, 'rosterFooterY', P(holder, '_y'))
            a.set(R, 'rosterScrollerY', P(P(display, 'mcTextScroller'), '_y'))
            a.set(R, 'rosterFooterCaptured', True)
        a.when(T('rosterFooterCaptured'), lambda a: None, capture)
        a.set(holder, '_y', FOOTER_Y)
        a.set(P(display, 'mcTextScroller'), '_y', FOOTER_Y)
    a.when(holder, place)


def restore(a):
    def reset(a):
        a.set(P(T('rosterFooterDisplay'), 'mcHelpItemsHolder'), '_y', T('rosterFooterY'))
        a.set(P(T('rosterFooterDisplay'), 'mcTextScroller'), '_y', T('rosterScrollerY'))
        a.set(R, 'rosterFooterCaptured', False)
    a.when(T('rosterFooterCaptured'), reset)
