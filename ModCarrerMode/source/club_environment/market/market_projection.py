"""Read-only transfer projection reused from New Experience; no UI/server imports."""
import datetime

POSITION_LABELS = ('GOL', 'LIB', 'ALA D', 'LD', 'ZAG D', 'ZAG', 'ZAG E', 'LE', 'ALA E', 'VOL D', 'VOL', 'VOL E', 'MD', 'MC D', 'MC', 'MC E', 'ME', 'MEI D', 'MEI', 'MEI E', 'SA D', 'SA', 'SA E', 'PD', 'ATA D', 'ATA', 'ATA E', 'PE')

def _display_name(player, names, edited):
    custom = edited.get(player['playerid'], {})
    for key in ('playerjerseyname', 'commonname'):
        if custom.get(key):
            return custom[key]
    common = names.get(player.get('commonnameid')) if player.get('commonnameid') else ''
    if common:
        return common
    first = custom.get('firstname') or names.get(player.get('firstnameid'), '')
    last = custom.get('surname') or names.get(player.get('lastnameid'), '')
    return ' '.join((part for part in (first, last) if part)) or f"Jogador {player['playerid']}"

class MarketProjection:

    @staticmethod
    def _career_date(value):
        try:
            text = str(int(value))
            if len(text) < 8:
                return None
            return datetime.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _window_payload(calendar, today):
        pairs = []
        if today and calendar.get('windowEndsValid'):
            for index in (1, 2):
                start = int(calendar.get(f'windowStart{index}', 0) or 0)
                end = int(calendar.get(f'windowEnd{index}', 0) or 0)
                if not (101 <= start <= 1231 and 101 <= end <= 1231):
                    continue
                try:
                    sm, sd = divmod(start, 100)
                    em, ed = divmod(end, 100)
                    datetime.date(today.year, sm, sd)
                    datetime.date(today.year, em, ed)
                    wraps = start > end
                    duration_start = datetime.date(today.year, sm, sd)
                    duration_end = datetime.date(today.year + (1 if wraps else 0), em, ed)
                    duration = (duration_end - duration_start).days + 1
                    if wraps:
                        if today.month * 100 + today.day >= start:
                            window_start = duration_start
                            window_end = duration_end
                        elif today.month * 100 + today.day <= end:
                            window_start = datetime.date(today.year - 1, sm, sd)
                            window_end = datetime.date(today.year, em, ed)
                        else:
                            window_start = datetime.date(today.year + 1, sm, sd)
                            window_end = datetime.date(today.year + 2, em, ed)
                    else:
                        window_start = duration_start
                        window_end = duration_end
                        if today > window_end:
                            window_start = datetime.date(today.year + 1, sm, sd)
                            window_end = datetime.date(today.year + 1, em, ed)
                    opened = window_start <= today <= window_end
                    pairs.append({'number': index, 'start': f'{sm:02d}/{sd:02d}', 'end': f'{em:02d}/{ed:02d}', 'startDate': window_start.isoformat(), 'endDate': window_end.isoformat(), 'durationDays': duration, 'open': opened, 'daysRemaining': (window_end - today).days if opened else None, 'daysUntilOpen': (window_start - today).days if not opened else 0})
                except (ValueError, OverflowError):
                    continue
        current = next((item for item in pairs if item['open']), None)
        upcoming = next((item for item in sorted((item for item in pairs if not item['open']), key=lambda item: item['daysUntilOpen'])), None)
        return {'careerDate': today.isoformat() if today else None, 'windows': pairs, 'current': current, 'next': upcoming, 'totalDurationDays': sum((item['durationDays'] for item in pairs)) if pairs else None}

    def transfer_market(self, active_club=0):
        with self.lock:
            self.refresh()
            if not self.db:
                raise ValueError('O save não contém os dados da carreira.')
            clubs = {int(row['id']): row for row in club_catalog() if row.get('id') is not None}
            team_names = {row['teamid']: row['teamname'] for row in self.base.rows('teams', ['teamid', 'teamname'])}
            try:
                active_club = int(active_club or 0)
            except (TypeError, ValueError):
                active_club = 0
            if active_club not in team_names:
                candidates = [club for club, manager in self.managers.items() if manager.get('clubteamid') == club]
                if len(candidates) != 1:
                    candidates = [club for club, manager in self.managers.items() if manager.get('teamid') == club]
                active_club = candidates[0] if len(candidates) == 1 else 0
            if self.transfer_market_cache and self.transfer_market_cache.get('saveRevision') == self.tag and (self.transfer_market_cache.get('clubId') == active_club):
                return self.transfer_market_cache
            saved_players = {row['playerid']: row for row in self.db.rows('players', ['playerid', 'commonnameid', 'firstnameid', 'lastnameid', 'overallrating', 'potential', 'preferredposition1'])}
            player_names = {row['nameid']: row['name'] for row in self.base.rows('playernames', ['nameid', 'name'])}
            if 'dcplayernames' in self.db.tables:
                player_names.update({row['nameid']: row['name'] for row in self.db.rows('dcplayernames', ['nameid', 'name']) if row.get('name')})
            edited = {row['playerid']: row for row in self.db.rows('editedplayernames', ['playerid', 'firstname', 'surname', 'commonname', 'playerjerseyname'])} if 'editedplayernames' in self.db.tables else {}
            current_teams = {}
            for row in self.db.rows('teamplayerlinks', ['teamid', 'playerid']):
                if row.get('playerid') and row.get('teamid'):
                    current_teams.setdefault(row['playerid'], set()).add(row['teamid'])
            career_date = self._career_date(self.calendar.get('careerDate'))
            deals = {}

            def club_info(team_id):
                item = clubs.get(int(team_id or 0), {})
                name = item.get('name') or team_names.get(team_id) or (f'Clube {team_id}' if team_id else 'Clube não identificado')
                return {'id': int(team_id) if team_id else None, 'name': name, 'crest': item.get('crest') or '', 'leagueId': item.get('leagueId'), 'leagueName': item.get('leagueName') or 'Liga não identificada', 'leagueIcon': item.get('leagueIcon') or ''}

            def keep_deal(player_id, seller, buyer, fee, raw_date, is_loan, source, offer_id=0):
                player = saved_players.get(player_id)
                if not player or not seller or (not buyer) or (seller == buyer):
                    return
                when = self._career_date(raw_date)
                if not when:
                    return
                name = _display_name(player, player_names, edited)
                key = (player_id, seller, buyer, when.year)
                position = player.get('preferredposition1')
                row = {'id': f'{player_id}-{seller}-{buyer}', 'playerId': player_id, 'playerName': name, 'overall': player.get('overallrating'), 'potential': player.get('potential'), 'position': POSITION_LABELS[position] if isinstance(position, int) and 0 <= position < len(POSITION_LABELS) else '', 'from': club_info(seller), 'to': club_info(buyer), 'date': when.isoformat(), 'fee': max(0, int(fee or 0)), 'loan': bool(is_loan), 'source': source, 'offerId': int(offer_id or 0)}
                old = deals.get(key)
                if old is None or (row['date'], row['offerId']) > (old['date'], old['offerId']):
                    deals[key] = row
            for offer in self.transfer_offers:
                if offer.get('result') != 32 or not offer.get('playerid'):
                    continue
                transfer_date = self._career_date(offer.get('date'))
                if not transfer_date or (career_date and transfer_date > career_date):
                    continue
                player_id = offer['playerid']
                members = current_teams.get(player_id, set())
                buyer_candidates = [offer.get('offerteamid'), offer.get('snipedteamid')]
                buyer = next((candidate for candidate in buyer_candidates if candidate and candidate > 0 and (candidate in members)), None)
                if not buyer:
                    continue
                keep_deal(player_id, offer.get('teamid'), buyer, offer.get('offeredfee'), offer.get('date'), offer.get('isloan'), 'transfer-offer', offer.get('offerid'))
            for contract in self.precontracts:
                completed = self._career_date(contract.get('completedate'))
                if not completed or (career_date and completed > career_date) or (not contract.get('playerid')):
                    continue
                player_id = contract['playerid']
                members = current_teams.get(player_id, set())
                buyer = contract.get('offerteamid')
                if buyer not in members:
                    continue
                keep_deal(player_id, contract.get('teamid'), buyer, 0, contract.get('completedate'), False, 'pre-contract', contract.get('offerid'))
            transfers = sorted(deals.values(), key=lambda item: (item['date'], item['playerName'].casefold()), reverse=True)
            leagues = {}
            buyers = {}
            sellers = {}
            investment = 0
            fee_volume = 0
            loan_count = 0
            purchase_count = 0
            for transfer in transfers:
                fee = transfer['fee']
                fee_volume += fee
                buyer = transfer['to']
                seller = transfer['from']
                is_loan = transfer['loan']
                if is_loan:
                    loan_count += 1
                else:
                    purchase_count += 1
                    investment += fee
                league_key = buyer['leagueId'] if buyer['leagueId'] is not None else 'unknown'
                league = leagues.setdefault(league_key, {'id': buyer['leagueId'], 'name': buyer['leagueName'], 'icon': buyer['leagueIcon'], 'investment': 0, 'feeVolume': 0, 'purchases': 0, 'loans': 0, 'deals': 0, 'clubs': set()})
                league['deals'] += 1
                league['feeVolume'] += fee
                league['clubs'].add(buyer['id'])
                if is_loan:
                    league['loans'] += 1
                else:
                    league['purchases'] += 1
                    league['investment'] += fee
                buy = buyers.setdefault(buyer['id'], {'id': buyer['id'], 'name': buyer['name'], 'leagueName': buyer['leagueName'], 'crest': buyer['crest'], 'investment': 0, 'purchases': 0, 'loans': 0, 'deals': 0})
                buy['deals'] += 1
                if is_loan:
                    buy['loans'] += 1
                else:
                    buy['purchases'] += 1
                    buy['investment'] += fee
                sell = sellers.setdefault(seller['id'], {'id': seller['id'], 'name': seller['name'], 'leagueName': seller['leagueName'], 'crest': seller['crest'], 'revenue': 0, 'sales': 0, 'loans': 0})
                if is_loan:
                    sell['loans'] += 1
                else:
                    sell['sales'] += 1
                    sell['revenue'] += fee
            leagues = [{**row, 'clubs': len(row['clubs'])} for row in leagues.values()]
            leagues.sort(key=lambda row: (-row['investment'], -row['purchases'], row['name'].casefold()))
            buyers = sorted(buyers.values(), key=lambda row: (-row['investment'], -row['purchases'], -row['deals'], row['name'].casefold()))
            sellers = sorted(sellers.values(), key=lambda row: (-row['revenue'], -row['sales'], row['name'].casefold()))
            managed_club = clubs.get(active_club, {})
            my_league_id = managed_club.get('leagueId')
            my_league = {'id': my_league_id, 'name': managed_club.get('leagueName') or 'Liga não identificada', 'icon': managed_club.get('leagueIcon') or '', 'clubId': active_club or None, 'clubName': managed_club.get('name') or team_names.get(active_club, 'Clube da carreira'), 'clubCrest': managed_club.get('crest') or '', 'summary': {'purchases': 0, 'sales': 0, 'loansIn': 0, 'loansOut': 0, 'investment': 0, 'revenue': 0, 'netSpend': 0, 'deals': 0}, 'clubs': [], 'transfers': []}
            if my_league_id is not None:
                league_transfers = [item for item in transfers if item['from']['leagueId'] == my_league_id or item['to']['leagueId'] == my_league_id]
                team_stats = {}

                def league_team(club):
                    return team_stats.setdefault(club['id'], {'id': club['id'], 'name': club['name'], 'crest': club['crest'], 'leagueName': club['leagueName'], 'purchases': 0, 'sales': 0, 'loansIn': 0, 'loansOut': 0, 'investment': 0, 'revenue': 0, 'netSpend': 0})
                purchases = sales = loans_in = loans_out = league_investment = league_revenue = 0
                for transfer in league_transfers:
                    buyer = transfer['to']
                    seller = transfer['from']
                    fee = transfer['fee']
                    if buyer['leagueId'] == my_league_id:
                        row = league_team(buyer)
                        if transfer['loan']:
                            loans_in += 1
                            row['loansIn'] += 1
                        else:
                            purchases += 1
                            league_investment += fee
                            row['purchases'] += 1
                            row['investment'] += fee
                    if seller['leagueId'] == my_league_id:
                        row = league_team(seller)
                        if transfer['loan']:
                            loans_out += 1
                            row['loansOut'] += 1
                        else:
                            sales += 1
                            league_revenue += fee
                            row['sales'] += 1
                            row['revenue'] += fee
                league_clubs = sorted(team_stats.values(), key=lambda row: (-row['investment'], -row['revenue'], -row['purchases'] - row['sales'], row['name'].casefold()))
                for row in league_clubs:
                    row['netSpend'] = row['investment'] - row['revenue']
                my_league['summary'] = {'purchases': purchases, 'sales': sales, 'loansIn': loans_in, 'loansOut': loans_out, 'investment': league_investment, 'revenue': league_revenue, 'netSpend': league_investment - league_revenue, 'deals': len(league_transfers)}
                my_league['clubs'] = league_clubs
                my_league['transfers'] = league_transfers
            payload = {'saveRevision': self.tag, 'clubId': active_club or None, 'careerDate': career_date.isoformat() if career_date else None, 'window': self._window_payload(self.calendar, career_date), 'summary': {'investment': investment, 'feeVolume': fee_volume, 'purchases': purchase_count, 'loans': loan_count, 'completedDeals': len(transfers), 'buyers': sum((1 for row in buyers if row['purchases'])), 'sellers': sum((1 for row in sellers if row['sales']))}, 'leagues': leagues, 'buyers': buyers, 'sellers': sellers, 'transfers': transfers, 'myLeague': my_league, 'note': 'Conta negócios concluídos que o save ainda registra e confirma no elenco do clube de destino. Propostas abertas e recusadas ficam fora; empréstimos aparecem separados das compras permanentes.'}
            self.transfer_market_cache = payload
            return payload
