const Icon = ({name, size = 14, stroke = 1.6, style}) => {
  const s = { width: size, height: size, display: 'inline-block', verticalAlign: 'middle', ...style };
  const p = { fill: 'none', stroke: 'currentColor', strokeWidth: stroke, strokeLinecap: 'round', strokeLinejoin: 'round' };
  switch(name) {
    case 'today': return <svg viewBox="0 0 16 16" style={s}><rect x="2.5" y="3.5" width="11" height="10" rx="1.5" {...p}/><path d="M5.5 2v3M10.5 2v3M2.5 6.5h11" {...p}/></svg>;
    case 'history': return <svg viewBox="0 0 16 16" style={s}><circle cx="8" cy="8" r="5.5" {...p}/><path d="M8 5v3l2 1.5" {...p}/></svg>;
    case 'portfolio': return <svg viewBox="0 0 16 16" style={s}><path d="M2.5 5.5h11v8h-11z" {...p}/><path d="M5.5 5.5V4a1.5 1.5 0 0 1 1.5-1.5h2a1.5 1.5 0 0 1 1.5 1.5v1.5" {...p}/></svg>;
    case 'accuracy': return <svg viewBox="0 0 16 16" style={s}><path d="M2.5 13.5V8M6 13.5V5M9.5 13.5V9.5M13 13.5V3" {...p}/></svg>;
    case 'hyp': return <svg viewBox="0 0 16 16" style={s}><path d="M5 6.5a3 3 0 1 1 6 0c0 1.5-1.5 2-1.5 3.5v.5h-3v-.5C6.5 8.5 5 8 5 6.5z" {...p}/><path d="M7 12.5h2M7.5 14h1" {...p}/></svg>;
    case 'feedback': return <svg viewBox="0 0 16 16" style={s}><path d="M2.5 4.5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H7l-3 2.5v-2.5h-.5a1 1 0 0 1-1-1z" {...p}/></svg>;
    case 'usage': return <svg viewBox="0 0 16 16" style={s}><circle cx="8" cy="8" r="5.5" {...p}/><path d="M8 4v4l2.5 1.5" {...p}/></svg>;
    case 'play': return <svg viewBox="0 0 16 16" style={s}><path d="M5 3.5l7 4.5-7 4.5z" fill="currentColor"/></svg>;
    case 'search': return <svg viewBox="0 0 16 16" style={s}><circle cx="7" cy="7" r="4.5" {...p}/><path d="M10.5 10.5l3 3" {...p}/></svg>;
    case 'chevron-right': return <svg viewBox="0 0 16 16" style={s}><path d="M6 4l4 4-4 4" {...p}/></svg>;
    case 'chevron-down': return <svg viewBox="0 0 16 16" style={s}><path d="M4 6l4 4 4-4" {...p}/></svg>;
    case 'check': return <svg viewBox="0 0 16 16" style={s}><path d="M3.5 8.5l3 3 6-7" {...p}/></svg>;
    case 'plus': return <svg viewBox="0 0 16 16" style={s}><path d="M8 3v10M3 8h10" {...p}/></svg>;
    case 'x': return <svg viewBox="0 0 16 16" style={s}><path d="M4 4l8 8M12 4l-8 8" {...p}/></svg>;
    case 'sparkle': return <svg viewBox="0 0 16 16" style={s}><path d="M8 2l1.5 4.5L14 8l-4.5 1.5L8 14l-1.5-4.5L2 8l4.5-1.5z" fill="currentColor"/></svg>;
    case 'wrench': return <svg viewBox="0 0 16 16" style={s}><path d="M10.5 2.5a3 3 0 0 0-4 4l-4 4 1.5 1.5 4-4a3 3 0 0 0 4-4l-1.5 1.5-1.5-.5-.5-1.5z" {...p}/></svg>;
    case 'memory': return <svg viewBox="0 0 16 16" style={s}><rect x="3.5" y="3.5" width="9" height="9" rx="1" {...p}/><path d="M3.5 6h9M3.5 10h9M6 3.5v9M10 3.5v9" {...p}/></svg>;
    case 'kite': return <svg viewBox="0 0 16 16" style={s}><path d="M8 1.5l6 6-6 6-6-6z" {...p}/><path d="M8 1.5v12" {...p}/></svg>;
    case 'arrow-up': return <svg viewBox="0 0 16 16" style={s}><path d="M8 12V4M4 8l4-4 4 4" {...p}/></svg>;
    case 'arrow-down': return <svg viewBox="0 0 16 16" style={s}><path d="M8 4v8M4 8l4 4 4-4" {...p}/></svg>;
    case 'pause': return <svg viewBox="0 0 16 16" style={s}><rect x="4.5" y="3.5" width="2.5" height="9" rx=".5" fill="currentColor"/><rect x="9" y="3.5" width="2.5" height="9" rx=".5" fill="currentColor"/></svg>;
    case 'refresh': return <svg viewBox="0 0 16 16" style={s}><path d="M13 4v3h-3M3 12V9h3" {...p}/><path d="M11.5 6a4 4 0 0 0-7 1M4.5 10a4 4 0 0 0 7-1" {...p}/></svg>;
    case 'eye': return <svg viewBox="0 0 16 16" style={s}><path d="M1.5 8s2.5-4.5 6.5-4.5S14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z" {...p}/><circle cx="8" cy="8" r="1.5" {...p}/></svg>;
    case 'settings': return <svg viewBox="0 0 16 16" style={s}><circle cx="8" cy="8" r="2" {...p}/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.5 3.5l1.4 1.4M11.1 11.1l1.4 1.4M3.5 12.5l1.4-1.4M11.1 4.9l1.4-1.4" {...p}/></svg>;
    case 'doc': return <svg viewBox="0 0 16 16" style={s}><path d="M4 2.5h6l3 3v8a.5.5 0 0 1-.5.5h-9V3a.5.5 0 0 1 .5-.5z" {...p}/><path d="M10 2.5V6h3" {...p}/></svg>;
    case 'graph': return <svg viewBox="0 0 16 16" style={s}><circle cx="3.5" cy="8" r="1.5" {...p}/><circle cx="12.5" cy="4" r="1.5" {...p}/><circle cx="12.5" cy="12" r="1.5" {...p}/><path d="M5 7.2L11 4.8M5 8.8L11 11.2" {...p}/></svg>;
    case 'database': return <svg viewBox="0 0 16 16" style={s}><ellipse cx="8" cy="4" rx="5" ry="1.5" {...p}/><path d="M3 4v8c0 .83 2.24 1.5 5 1.5s5-.67 5-1.5V4M3 8c0 .83 2.24 1.5 5 1.5s5-.67 5-1.5" {...p}/></svg>;
    default: return null;
  }
};

window.Icon = Icon;
