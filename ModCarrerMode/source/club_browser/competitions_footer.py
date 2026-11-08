"""Use FIFA's own HelpItem symbols and HelpManager for every competition view."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'club_environment/manager_market'))

# These names are native FIFA input bindings, not manually drawn keycaps.
MODES=(
    (('BACK','Voltar'),),
    (('ADVANCE','Selecionar'),('BACK','Voltar'),('L1R1','Competições'),('LAS_LR','Cards'),('RAS_UD','Rolar tela')),
    (('BACK','Voltar'),('L1R1','Ranking'),('LAS_UD','Jogadores'),('RAS_UD','Rolar lista')),
    (('BACK','Voltar'),('ADVANCE','Ajustar'),('LAS_LR','Mover'),('RAS_LR','Fases'),('L2R2','Zoom')),
    (('BACK','Voltar'),('L2R2','Rodadas'),('LAS_UD','Jogos'),('RAS_UD','Rolar lista')),
)

def build_states(game,folder):
    from live_payload import build
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for mode in range(len(MODES)):
        build(game,folder/('mode_'+str(mode)+'.big'),dict(kind='competition_help',mode=mode))

def emit(a):
    import build_screen as b
    from live_payload import emit as live_emit
    R=b.reg;T=b.this;P=b.prop;CALL=b.call;EQ=b.equal
    both=lambda x,y:('bin',16,x,y)
    def received(a,data):
        mode=P(data,'mode')
        a.when(('not',EQ(mode,T('footerMode'))),lambda a:(a.set(R(1),'footerMode',mode),a.do(R(1),'RefreshHelp')))
    live_emit(a,'competitionHelp','competitionhelp',lambda d:both(EQ(P(d,'kind'),'competition_help'),both(('bin',103,P(d,'mode'),0),('bin',72,P(d,'mode'),len(MODES)))),received,interval=12)
    def help_context(a):
        for mode,items in enumerate(MODES):
            a.when(EQ(T('footerMode'),mode),lambda a,items=items:a.ret(('array',tuple(CALL(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in items))))
        a.ret(('array',(CALL(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar'),)))
    a.function('getHelpContext',0,help_context)
