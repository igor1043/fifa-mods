"""Own the photograph clips only while the trophy room is ready and visible.

BackgroundBootflow is a static ImageLoader. BackgroundFIFA subscribes once,
then unregisters after its first image. Provider refresh alone cannot remove
either already-mounted photograph reliably. Listen to the same native
BackgroundDP as FIFA and preserve/restore the actual clip visibility.
"""


def emit(a,b):
    R,T,P,CALL,PATH,EQ=b.reg,b.this,b.prop,b.call,b.path,b.equal
    provider=PATH('game','uif','UIFDataProviderList','BackgroundDP')
    utility=PATH('game','uif','UIFUtility')
    owners=[b.G('Server16ManagerFaceBootBackgroundOwner'),b.G('Server16ManagerFaceBackgroundOwner')]
    nodes=[owners[0],P(owners[0],'mcImageLoader'),owners[1],P(owners[1],'mcImage')]

    def restore_node(a,node):
        a.when(P(node,'S16TrophyCoverHidden'),lambda a:(
            a.set(node,'_visible',P(node,'S16TrophyCoverVisible')),
            a.set(node,'S16TrophyCoverHidden',False)))

    def sync(a):
        # Native mouse/controller handlers can switch the presentation before
        # the APT receives an input alias. The provider, not that local alias,
        # is the authoritative indication that the 3D room may be uncovered.
        hide=T('backgroundReady')
        for i,node in enumerate(nodes):
            saved=T('coverNode'+str(i))
            a.when(('not',EQ(saved,node)),lambda a,saved=saved:restore_node(a,saved))
            a.set(R(1),'coverNode'+str(i),node)
            def conceal(a,node=node):
                a.when(P(node,'S16TrophyCoverHidden'),lambda a:None,
                       lambda a:a.set(node,'S16TrophyCoverVisible',P(node,'_visible')))
                a.set(node,'S16TrophyCoverHidden',True);a.set(node,'_visible',False)
            a.when(node,lambda a,node=node,conceal=conceal:a.when(hide,conceal,lambda a:restore_node(a,node)))
    a.function('SyncBackgroundCover',0,sync)

    def publish(a):
        a.when(('not',EQ(R(3),provider)),lambda a:a.ret())
        dp=('newmethod',PATH('game','uif','DataProviders'),'BackgroundDP',(R(2),0))
        a.set(R(1),'backgroundReady',EQ(CALL(dp,'GetParam'),'server16_frontend_clear'))
        a.do(R(1),'SyncBackgroundCover')
    a.function('Publish',2,publish)

    def register(a):
        a.set(R(1),'backgroundReady',False)
        a.do(utility,'RegisterDataProvider',R(1),provider)
    a.function('RegisterBackgroundCover',0,register)

    def restore(a):
        a.do(utility,'UnregisterDataProvider',R(1))
        for i in range(len(nodes)):restore_node(a,T('coverNode'+str(i)))
        a.set(R(1),'backgroundReady',False)
    a.function('RestoreBackgroundCover',0,restore)
