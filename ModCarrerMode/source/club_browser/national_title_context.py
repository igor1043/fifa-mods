"""Read the second native career team slot; never call or write into FIFA."""
import struct

TEAM_GETTER=bytes.fromhex('83fa0177114863c2486bc0744805a00100004801c8c3')

def live_team(memory,profile):
    if not callable(getattr(memory,'read_process_memory',None)) or not getattr(memory,'base_module',0):
        raise ValueError('Aguardando leitura dos vínculos da carreira')
    if memory.read_process_memory(memory.base_module+0x5ac5940,len(TEAM_GETTER))!=TEAM_GETTER:
        raise ValueError('Layout dos vínculos da carreira incompatível')
    # The verified getter accepts slots 0/1, with 0x74-byte records at +0x1a0.
    # Both records use the same team-id field, +4. Confirm the known club first.
    context=profile['context_address']
    club=struct.unpack('<i',memory.read_process_memory(context+0x1a4,4))[0]
    nation=struct.unpack('<i',memory.read_process_memory(context+0x1a0+0x74+4,4))[0]
    if club!=profile['club_id'] or not -1<=nation<=2000000:
        raise ValueError('Vínculo de outra carreira')
    return max(0,nation)

def observations(user,manager,saved_date,today,teams,memory=None,profile=None):
    """Only dated evidence; no claim that a first national job began at save start."""
    values={r for r in (user.get('nationalteamid'),manager.get('internationalteamid')) if r is not None and r>0}
    result=[]
    if len(values)<=1:
        team=next(iter(values),0)
        if team==0 or team in teams:result.append(dict(date=saved_date,team=team,source='saved_user'))
    if memory is not None and profile is not None:
        try:
            team=live_team(memory,profile)
            if team==0 or team in teams:result.append(dict(date=today,team=team,source='live_context'))
        except (OSError,RuntimeError,ValueError,KeyError):pass
    return result
