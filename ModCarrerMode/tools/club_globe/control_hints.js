(() => {
  const escapeText = value => String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[character]));

  class FifaControlHints extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: 'open' });
      this.options = { mode: 'keyboard', controllerId: '', actions: null };
    }

    connectedCallback() { this.render(); }

    configure(options = {}) {
      this.options = { ...this.options, ...options };
      this.render();
    }

    defaultActions(mode, controllerId) {
      if (this.options.view === 'details') {
        if (mode !== 'gamepad') return [
          ...(this.options.canActivate?[{key:'Enter',label:this.options.activateLabel||'Abrir'}]:[]),
          { key: 'Esc', label: 'Voltar ao mapa' },
          { key: '↑ ↓ ← →', label: 'Navegar pelos cards' },
          { key: 'Roda', label: 'Rolar retrospecto' },
        ];
        const id = controllerId.toLowerCase();
        const playstation = /playstation|dualshock|dualsense|sony|054c/.test(id);
        const nintendo = /nintendo|switch|joy.con/.test(id);
        const family = playstation ? 'playstation' : nintendo ? 'nintendo' : /xbox|x-box|microsoft|045e|xinput/.test(id) ? 'xbox' : 'generic';
        const face = playstation ? 'circle' : nintendo ? 'a' : 'b';
        const glyph = playstation ? '○' : nintendo ? 'A' : 'B';
        return [
          ...(this.options.canActivate?[{key:playstation?'×':'A',face:playstation?'cross':'a',family,label:this.options.activateLabel||'Abrir'}]:[]),
          { key: glyph, glyph, face, family, label: 'Voltar ao mapa' },
          { keys: [{ key: 'L', family: 'stick' }, { key: 'D-pad', family: 'dpad' }], label: 'Navegar pelos cards' },
          { key: 'R', family: 'stick', label: 'Rolar retrospecto' },
        ];
      }
      if (mode !== 'gamepad') return [
        { key: '↑ ↓', label: 'Mudar foco' },
        { key: '← →', label: 'Percorrer seleção' },
        { key: 'Enter', label: 'Confirmar clube' },
        { key: 'Esc', label: 'Voltar ao save' },
        { key: 'R', label: 'Centralizar sem mudar o zoom' },
        { key: '+ / −', label: 'Aproximar / afastar' },
      ];

      const id = controllerId.toLowerCase();
      const playstation = /playstation|dualshock|dualsense|sony|054c/.test(id);
      const nintendo = /nintendo|switch|joy.con/.test(id);
      const xbox = /xbox|x-box|microsoft|045e|xinput/.test(id);
      const family = playstation ? 'playstation' : nintendo ? 'nintendo' : xbox ? 'xbox' : 'generic';
      const button = (face, glyph) => ({ key: glyph, glyph, face, family });
      return [
        { keys: [{ key: 'L', family: 'stick' }, { key: 'D-pad', family: 'dpad' }], label: 'Navegar seleção' },
        { key: 'R', family: 'stick', label: 'Girar o globo' },
        { ...button(playstation ? 'cross' : nintendo ? 'b' : 'a', playstation ? '×' : nintendo ? 'B' : 'A'), label: 'Confirmar clube' },
        { ...button(playstation ? 'circle' : nintendo ? 'a' : 'b', playstation ? '○' : nintendo ? 'A' : 'B'), label: 'Voltar ao save' },
        { ...button(playstation ? 'triangle' : nintendo ? 'x' : 'y', playstation ? '△' : nintendo ? 'X' : 'Y'), label: 'Centralizar sem mudar o zoom' },
        { key: playstation ? 'R1' : nintendo ? 'R' : 'RB', label: 'Aproximar rápido' },
        { key: playstation ? 'R2' : nintendo ? 'ZR' : 'RT', label: 'Aproximar' },
        { key: playstation ? 'L2' : nintendo ? 'ZL' : 'LT', label: 'Afastar' },
      ];
    }

    render() {
      if (!this.shadowRoot) return;
      const mode = this.options.mode === 'gamepad' ? 'gamepad' : 'keyboard';
      const actions = this.options.actions || this.defaultActions(mode, this.options.controllerId || '');
      if(parent!==window && !new URLSearchParams(location.search).has('overlay') && !this.options.actions){actions.forEach(a=>{if(a.label==='Voltar ao save')a.label='Voltar à central';});const quick=actions.findIndex(a=>a.label==='Aproximar rápido');if(quick>=0)actions.splice(quick,1);actions.push({key:mode==='gamepad'?(/sony|054c|playstation|dual/i.test(this.options.controllerId)?'L1 / R1':'LB / RB'):'Q / E',label:'Alternar abas'});}
      const items = actions.map(item => {
        const renderKey = keyItem => {
          const buttonClass = keyItem.face ? `controller-key ${escapeText(keyItem.family)} ${escapeText(keyItem.face)}`
            : keyItem.family === 'stick' ? 'controller-key stick-key'
              : keyItem.family === 'dpad' ? 'controller-key dpad-key' : '';
          if (keyItem.family === 'dpad') {
            return `<span class="${buttonClass}" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3v18M3 12h18M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3"/></svg></span>`;
          }
          return buttonClass
            ? `<span class="${buttonClass}" aria-hidden="true">${escapeText(keyItem.glyph || keyItem.key)}</span>`
            : `<kbd>${escapeText(keyItem.key)}</kbd>`;
        };
        const keys = item.keys || [item];
        return `<span class="item"><span class="keys">${keys.map(renderKey).join('')}</span><span>${escapeText(item.label)}</span></span>`;
      }).join('');
      this.shadowRoot.innerHTML = `
        <style>
          :host{display:block;color:#e7eef5;font-family:Manrope,"Segoe UI",sans-serif}
          .bar{min-height:42px;display:flex;align-items:center;justify-content:center;gap:4px 0;flex-wrap:wrap;padding:4px 10px;border-top:1px solid #2a3a49;background:linear-gradient(180deg,#0b1420f5,#070c13f8);box-shadow:0 -8px 22px #0003}
          .item{display:inline-flex;align-items:center;gap:5px;padding:0 9px;border-right:1px solid #263544;font-size:10px;line-height:1.15;color:#a9bbca;white-space:nowrap}
          .item:last-child{border-right:0}
          .keys{display:inline-flex;align-items:center;gap:3px}
          kbd{min-width:24px;min-height:22px;display:inline-flex;align-items:center;justify-content:center;padding:2px 6px;border:1px solid #52687b;border-radius:5px;background:linear-gradient(#25394b,#172637);box-shadow:0 2px 0 #080d13;color:#f3f8fc;font:700 11px/1 Manrope,"Segoe UI",sans-serif;text-shadow:0 1px 2px #000}
          .controller-key{width:23px;height:23px;flex:none;display:inline-flex;align-items:center;justify-content:center;border:1px solid #617486;border-radius:50%;background:#172331;box-shadow:none;color:#e1eaf1;font:600 11px/1 Manrope,"Segoe UI",sans-serif;text-shadow:none}
          .stick-key{font-size:9px;letter-spacing:-.5px}
          .dpad-key svg{width:13px;height:13px;fill:none;stroke:#e1eaf1;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
          @media(max-width:760px){.bar{justify-content:center;padding:4px 5px;gap:3px 0}.item{padding:0 5px;gap:4px;font-size:9px}.controller-key{width:21px;height:21px;font-size:10px}kbd{min-width:20px;min-height:19px;font-size:9px;padding:1px 3px}}
          @media(max-height:760px){.bar{min-height:34px;padding:3px 6px;gap:2px 0}.item{padding:0 6px;font-size:9px;gap:4px}.controller-key{width:21px;height:21px;font-size:10px}kbd{min-width:20px;min-height:19px;padding:1px 3px}}
          @media(max-height:520px){.bar{min-height:29px;padding:2px 4px;gap:1px 0}.item{padding:0 4px;font-size:8px;gap:3px}.controller-key{width:18px;height:18px;font-size:9px}kbd{min-width:17px;min-height:17px;font-size:8px}}
        </style>
        <nav class="bar" aria-label="Atalhos de ${mode === 'gamepad' ? 'controle' : 'teclado'}">${items}</nav>`;
      this.dataset.mode = mode;
      this.dataset.view = this.options.view || 'globe';
    }
  }

  if (!customElements.get('ff-control-hints')) customElements.define('ff-control-hints', FifaControlHints);
  window.FFControlHints = {
    mount(element, options) {
      if (!element || typeof element.configure !== 'function') {
        throw new TypeError('FFControlHints precisa de um elemento <ff-control-hints>.');
      }
      element.configure(options);
      return element;
    },
  };
})();
