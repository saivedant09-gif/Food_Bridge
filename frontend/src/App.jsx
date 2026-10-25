import React, { useEffect, useState, useId } from 'react';
import { api, API_BASE } from './api.js';

const pages = ['Overview', 'Find food', 'Share food', 'Requests', 'Reviews'];
const paths = ['overview', 'food', 'share', 'requests', 'reviews'];
const symbols = ['◫', '◉', '↗', '⇄', '☆'];
const quantity = value => Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
const dateTime = value => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not specified' : date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};
const available = food => food.status === 'AVAILABLE' && Number(food.available_quantity) > 0 && new Date(food.pickup_deadline) > new Date();

function useResource(path, refresh) {
  const [state, setState] = useState({ loading: true, data: null, error: '' });
  useEffect(() => {
    const controller = new AbortController();
    setState({ loading: true, data: null, error: '' });
    api(path, { signal: controller.signal }).then(data => setState({ loading: false, data, error: '' }))
      .catch(error => { if (!controller.signal.aborted) setState({ loading: false, data: null, error: error.message }); });
    return () => controller.abort();
  }, [path, refresh]);
  return state;
}

function Notice({ error, children }) {
  return <div className={`notice ${error ? 'error' : 'success'}`} role={error ? 'alert' : 'status'}>{children}</div>;
}
function Field({ label, hint, ...props }) {
  const id = useId();
  return <div className="field"><label htmlFor={id}>{label}</label><input id={id} aria-describedby={hint ? `${id}-hint` : undefined} required {...props}/>{hint && <small id={`${id}-hint`}>{hint}</small>}</div>;
}
function UserSelect({ role, name, label, valueKey = 'user_id' }) {
  const users = useResource(`/users?role=${role}`, 0);
  return <div className="field"><label htmlFor={`user-${name}`}>{label}</label><select id={`user-${name}`} name={name} required defaultValue=""><option value="">{users.loading ? 'Loading users…' : `Select a ${role === 'DONOR' ? 'donor' : 'NGO'}`}</option>{users.data?.map(user => <option key={user.user_id} value={user[valueKey]}>{user.name}{user.location ? ` · ${user.location}` : ''}</option>)}</select>{users.error && <Notice error>{users.error}</Notice>}{users.data?.length === 0 && <small>No {role.toLowerCase()} users exist in the database.</small>}</div>;
}
function Badge({ children }) { return <span className={`badge ${children === 'AVAILABLE' ? 'green' : ''}`}>{String(children).toLowerCase().replaceAll('_', ' ')}</span>; }
function Empty({ title, children }) { return <div className="empty"><span aria-hidden="true">♧</span><h3>{title}</h3><p>{children}</p></div>; }

function MutationForm({ children, submit, label, onDone, validate, reset = true }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  async function handleSubmit(event) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setError(''); setResult(null);
    const problem = validate?.(data);
    if (problem) { setError(problem); return; }
    setBusy(true);
    try {
      const response = await submit(data);
      setResult(response);
      if (reset) form.reset();
      onDone?.(response);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <form onSubmit={handleSubmit} className="form"><fieldset disabled={busy}>{children}</fieldset>
    {error && <Notice error>{error}</Notice>}
    {result && <Notice>{result.message}{result.food_id && ` · Food #${result.food_id}`}{result.request_id && ` · Request #${result.request_id}`}{result.status && ` · ${result.status}`}{result.remaining_quantity != null && ` · Remaining quantity: ${quantity(result.remaining_quantity)}`}{result.review_id && ` · Review ID: ${result.review_id}`}</Notice>}
    <button className="button primary" disabled={busy}>{busy ? 'Saving…' : label} <span aria-hidden="true">↗</span></button></form>;
}

function FoodCard({ food, onRequest }) {
  const canRequest = available(food);
  return <article className="food-card"><div className="food-art" aria-hidden="true"><svg viewBox="0 0 240 110"><path d="M40 40h160a80 65 0 0 1-160 0" fill="#e8dcc0"/><path d="M52 38c8-25 29-18 40-10 10-28 34-24 42-6 22-23 45-6 49 16" fill="#8aab76"/><path d="M73 36c10-10 20-9 25 1m37-1c9-14 21-13 29 0" fill="none" stroke="#d4b169" strokeWidth="10" strokeLinecap="round"/><path d="M35 41h170" stroke="#567d56" strokeWidth="4" strokeLinecap="round"/></svg><span>FOOD TO SHARE</span></div>
    <div className="food-content"><div className="card-top"><Badge>{canRequest ? 'AVAILABLE' : food.status === 'AVAILABLE' ? 'EXPIRED' : food.status}</Badge><span className="muted">#{food.food_id}</span></div><h3>{food.food_name}</h3><p className="donor">{food.donor_name} <span>· {food.location || 'Location not specified'}</span></p><div className="food-details"><div><small>Available</small><strong>{quantity(food.available_quantity)} <span>{food.unit}</span></strong></div><div><small>Pick up by</small><strong className="deadline">{dateTime(food.pickup_deadline)}</strong></div></div><button className="button outline" disabled={!canRequest} onClick={() => onRequest(food)}>{canRequest ? 'Request food' : 'Unavailable'} <span aria-hidden="true">→</span></button></div></article>;
}

function FoodList({ resource, onRequest, retry, limit, filters = false }) {
  const [search, setSearch] = useState('');
  const [onlyAvailable, setOnlyAvailable] = useState(true);
  const food = (resource.data || []).filter(item => (!onlyAvailable || available(item)) && `${item.food_name} ${item.donor_name} ${item.location}`.toLowerCase().includes(search.toLowerCase()));
  return <>{filters && <div className="filter-bar"><label className="search"><span aria-hidden="true">⌕</span><input aria-label="Search food, donor or location" placeholder="Search food, donor or location…" value={search} onChange={e => setSearch(e.target.value)}/></label><label className="check"><input type="checkbox" checked={onlyAvailable} onChange={e => setOnlyAvailable(e.target.checked)}/> Available only</label><button className="button subtle" onClick={retry}>↻ Refresh</button></div>}
    {resource.loading ? <div className="loading" role="status">Loading food from your community…</div> : resource.error ? <Notice error><strong>Food listings are unavailable.</strong> {resource.error} <button className="text-button" onClick={retry}>Try again</button></Notice> : food.length ? <div className="food-grid">{food.slice(0, limit || food.length).map(item => <FoodCard key={item.food_id} food={item} onRequest={onRequest}/>)}</div> : <Empty title="A little room for more generosity">{search ? 'No food matches your search. Try another food or location.' : 'No available food listings right now. Share surplus food to get things started.'}</Empty>}</>;
}

function ShareFood({ refresh }) {
  return <div className="two-column"><section className="panel"><div className="section-title"><span className="step">01</span><div><h2>Make your surplus count.</h2><p>A few details help NGOs plan a safe, timely pickup.</p></div></div><MutationForm label="Publish food listing" onDone={refresh} validate={data => new Date(data.pickup_deadline) <= new Date(data.prepared_at) ? 'Pickup deadline must be after preparation time.' : new Date(data.pickup_deadline) <= new Date() ? 'Choose a pickup deadline in the future.' : ''} submit={data => api('/food', { method: 'POST', body: { ...data, donor_id: Number(data.donor_id), quantity: Number(data.quantity), food_name: data.food_name.trim(), unit: data.unit.trim() } })}>
    <UserSelect role="DONOR" name="donor_id" label="Donor"/>
    <Field label="Food name" name="food_name" minLength="2" maxLength="150" placeholder="e.g. Freshly prepared vegetable rice" pattern=".*\S.*"/>
    <div className="form-row"><Field label="Quantity" name="quantity" type="number" min="0.01" max="1000000" step="0.01" placeholder="25"/><Field label="Unit" name="unit" maxLength="30" placeholder="e.g. portions, kg, boxes" pattern=".*\S.*"/></div>
    <div className="form-row"><Field label="Prepared at" name="prepared_at" type="datetime-local"/><Field label="Pickup deadline" name="pickup_deadline" type="datetime-local"/></div>
  </MutationForm></section><aside className="guide"><span className="eyebrow">A GOOD DONATION STARTS HERE</span><h2>Good food.<br/>Thoughtful sharing.</h2><p>Share food that you would be happy to serve at your own table.</p><ul><li>Describe your food clearly and use a consistent quantity unit.</li><li>Set a realistic pickup window while the food is safe to eat.</li><li>Keep your request ID when an NGO reaches out.</li></ul><div className="demo-note">This is a local project workspace. Donor and NGO IDs identify existing database records; they are not authenticated accounts.</div></aside></div>;
}

function Requests({ selectedFood, refresh, role, refreshKey, foodResource, requestResource }) {
  const [mode, setMode] = useState(role === 'DONOR' ? 'approve' : 'request');
  const [activeRequest, setActiveRequest] = useState('');
  const choices = role === 'DONOR' ? ['approve', 'reject'] : ['request', 'collect'];
  useEffect(() => { setMode(role === 'DONOR' ? 'approve' : 'request'); setActiveRequest(''); }, [role]);
  const rows = requestResource.data || [];
  const eligible = rows.filter(row => row.status === (mode === 'collect' ? 'APPROVED' : 'PENDING'));
  const foodOptions = (foodResource.data || []).filter(available);
  const selected = rows.find(row => String(row.request_id) === String(activeRequest));
  const finish = () => {setActiveRequest('');refresh();};
  const chooseAction = (row, action) => {setMode(action);setActiveRequest(String(row.request_id));document.getElementById('request-form')?.scrollIntoView({behavior:'smooth',block:'start'});};
  const requestField = <div className="field"><label htmlFor="request-id">Request</label><select id="request-id" name="request_id" required value={activeRequest} onChange={event => setActiveRequest(event.target.value)}><option value="">Select {mode === 'collect' ? 'an approved' : 'a pending'} request</option>{eligible.map(row => <option key={row.request_id} value={row.request_id}>#{row.request_id} · {row.food_name} · {row.ngo_name} · {quantity(row.requested_quantity)} {row.unit}</option>)}</select>{!eligible.length && <small>No eligible requests. Refresh after creating or approving a request.</small>}</div>;
  return <><div className="two-column"><section className="panel" id="request-form"><h2>Move a donation forward</h2><p className="muted">Choose a donation and follow its progress through the community.</p><div className="tabs">{choices.map(value => <button key={value} onClick={() => {setMode(value);setActiveRequest('');}} aria-pressed={mode === value} className={mode === value ? 'active' : ''}>{({request:'Request food',approve:'Approve',reject:'Reject',collect:'Record collection'})[value]}</button>)}</div>
  {mode === 'request' && <MutationForm key={`request-${selectedFood?.food_id || ''}`} label="Send donation request" onDone={refresh} validate={data => {
    const current = foodOptions.find(item => item.food_id === Number(data.food_id));
    return !current ? 'Select an available food listing.' : Number(data.requested_quantity) > Number(current.available_quantity) ? 'Requested quantity exceeds current availability.' : '';
  }} submit={data => api('/requests', {method:'POST',body:{food_id:Number(data.food_id),ngo_id:Number(data.ngo_id),requested_quantity:Number(data.requested_quantity)}})}>
    <div className="field"><label htmlFor="request-food">Food donation</label><select id="request-food" name="food_id" required defaultValue={foodOptions.some(item => item.food_id === selectedFood?.food_id) ? selectedFood.food_id : ''}><option value="">Select available food</option>{foodOptions.map(item => <option key={item.food_id} value={item.food_id}>{item.food_name} · {quantity(item.available_quantity)} {item.unit} · {item.donor_name}</option>)}</select>{!foodOptions.length && <small>No food is currently available. Publish a new listing with a future pickup deadline.</small>}</div>
    <UserSelect role="NGO" name="ngo_id" label="NGO"/><Field label="Requested quantity" name="requested_quantity" type="number" step="0.01" min="0.01" max="1000000"/>
  </MutationForm>}
  {['approve','reject'].includes(mode) && <MutationForm key={mode} label={mode === 'approve' ? 'Approve request' : 'Reject request'} onDone={finish} submit={data => api(`/requests/${Number(data.request_id)}/${mode}`, {method:'PUT'})}>
    <Notice>{mode === 'approve' ? 'Approval reserves the requested quantity immediately. The API checks remaining availability and pickup time.' : 'Rejecting a pending request does not change the food quantity.'}</Notice>{requestField}
  </MutationForm>}
  {mode === 'collect' && <MutationForm key="collect" label="Confirm food collection" onDone={finish} submit={data => api(`/requests/${Number(data.request_id)}/collect`, {method:'POST',body:{collected_quantity:Number(data.collected_quantity),notes:data.notes.trim()}})}>
    <Notice>Record the actual handoff. This completes the request; any uncollected reserved quantity becomes available again while the pickup window is open.</Notice>{requestField}<Field key={activeRequest} label="Collected quantity" name="collected_quantity" type="number" min="0.01" max={selected?.requested_quantity || 1000000} step="0.01" defaultValue={selected?.requested_quantity}/><Field label="Collection notes (optional)" name="notes" maxLength="255" required={false}/>
  </MutationForm>}
  </section><aside className="guide"><span className="eyebrow">FROM SURPLUS TO SUPPORT</span><h2>Every handoff<br/>makes a difference.</h2><ol className="workflow"><li><strong>Request</strong><p>Select an NGO and available food.</p></li><li><strong>Approve</strong><p>Switch to the donor workspace to reserve the quantity.</p></li><li><strong>Collect</strong><p>Switch to the NGO workspace and record the handoff.</p></li></ol><div className="demo-note">Local project workspace. Role selection changes the view; the existing backend does not provide account sign-in.</div></aside></div>
  <section className="panel request-history"><div className="section-header"><div><span className="eyebrow">EVERY HANDOFF, IN ONE PLACE</span><h2>Donation requests</h2></div><button className="button subtle" onClick={refresh}>↻ Refresh</button></div>
  {requestResource.loading ? <div className="loading" role="status">Loading requests…</div> : requestResource.error ? <Notice error>{requestResource.error}</Notice> : !rows.length ? <Empty title="Start a new connection">Requests will appear here after an NGO chooses a food donation.</Empty> : <div className="table-scroll"><table><thead><tr><th>Donation</th><th>Community</th><th>Quantity</th><th>Status</th><th>Next step</th></tr></thead><tbody>{rows.map(row => <tr key={row.request_id}><td><strong>{row.food_name}</strong><small>Request #{row.request_id} · Food #{row.food_id}</small></td><td>{row.ngo_name}<small>From {row.donor_name}</small></td><td>{quantity(row.requested_quantity)} {row.unit}{row.collected_quantity != null && <small>{quantity(row.collected_quantity)} collected</small>}</td><td><Badge>{row.status}</Badge></td><td>{row.status === 'PENDING' && role === 'DONOR' ? <div className="row-actions"><button className="text-button" disabled={new Date(row.pickup_deadline) <= new Date()} onClick={() => chooseAction(row,'approve')}>Approve</button><button className="text-button" onClick={() => chooseAction(row,'reject')}>Reject</button></div> : row.status === 'APPROVED' && role === 'NGO' ? <button className="text-button" onClick={() => chooseAction(row,'collect')}>Record collection</button> : <small>{row.status === 'COMPLETED' ? 'Collection recorded' : row.status === 'REJECTED' ? 'Request closed' : row.status === 'PENDING' ? 'Awaiting donor' : 'Awaiting NGO'}</small>}</td></tr>)}</tbody></table></div>}
  </section></>;
}

function Reviews({ refreshKey, refresh, foodResource }) {
  const [reviewFoodId, setReviewFoodId] = useState('');
  const reviewFood = foodResource.data?.find(item => String(item.food_id) === reviewFoodId);
  const [filter, setFilter] = useState('');
  const [foodId, setFoodId] = useState('');
  const resource = useResource(foodId ? `/reviews/${foodId}` : '/reviews', refreshKey);
  return <div className="two-column reviews-layout"><section><div className="panel compact"><form className="filter-bar" onSubmit={event => {event.preventDefault(); setFoodId(filter);}}><label className="search"><input aria-label="Filter reviews by food ID" type="number" min="1" step="1" placeholder="Filter by food ID" value={filter} onChange={event => setFilter(event.target.value)}/></label><button className="button outline">Filter</button><button type="button" className="text-button" onClick={() => {setFilter('');setFoodId('');refresh();}}>Reset</button></form></div>
    {resource.loading ? <div className="loading" role="status">Loading community reviews…</div> : resource.error ? <Notice error>{resource.error} <button className="text-button" onClick={refresh}>Try again</button></Notice> : resource.data?.reviews.length ? <div className="review-list">{resource.data.reviews.map((review,index) => <article className="panel review" key={index}><div className="card-top"><span className="stars" aria-label={`${review.rating} out of 5 stars`}>{'★'.repeat(review.rating)}{'☆'.repeat(5-review.rating)}</span><span className="muted">{review.review_date}</span></div><h3>{review.food_name}</h3><p className="feedback">{review.feedback}</p><div className="review-footer"><strong>{review.reviewer_ngo}</strong><span>Food #{review.food_id} · {quantity(review.quantity_received)} received</span></div></article>)}</div> : <Empty title="The next good story could be yours">No reviews {foodId ? 'for this food ID' : 'yet'}. Share feedback after your food collection.</Empty>}
  </section><section className="panel"><h2>Share your experience</h2><p className="muted">Help the community make every donation better.</p><MutationForm label="Submit review" onDone={() => {setReviewFoodId('');refresh();}} submit={data => api('/reviews', {method:'POST',body:{...data,food_id:Number(data.food_id),rating:Number(data.rating),quantity_received:Number(data.quantity_received),food_name:data.food_name.trim(),reviewer_ngo:data.reviewer_ngo.trim(),feedback:data.feedback.trim()}})}>
    <div className="field"><label htmlFor="review-food">Food donation</label><select id="review-food" name="food_id" required value={reviewFoodId} onChange={event => setReviewFoodId(event.target.value)}><option value="">Select the food you received</option>{foodResource.data?.map(item => <option key={item.food_id} value={item.food_id}>{item.food_name} · #{item.food_id}</option>)}</select></div><Field label="Food name" name="food_name" value={reviewFood?.food_name || ''} readOnly/><UserSelect role="NGO" name="reviewer_ngo" label="NGO" valueKey="name"/>
    <div className="form-row"><div className="field"><label htmlFor="review-rating">Rating</label><select id="review-rating" name="rating" required defaultValue="5">{[5,4,3,2,1].map(value => <option key={value} value={value}>{value} {value === 1 ? 'star' : 'stars'}</option>)}</select></div><Field label="Quantity received" name="quantity_received" type="number" min="0.01" step="any"/></div><Field label="Review date" name="review_date" type="date" defaultValue={new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0,10)}/><label className="field"><span>Your feedback</span><textarea name="feedback" required maxLength="3000" rows="4" placeholder="How was your collection experience?"/></label>
  </MutationForm></section></div>;
}

export default function App() {
  const [page, setPage] = useState(() => paths.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'overview');
  const [role, setRole] = useState('NGO');
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedFood, setSelectedFood] = useState(null);
  const [menuOpen,setMenuOpen] = useState(false);
  const [status,setStatus] = useState('Checking API');
  const food = useResource('/food',refreshKey);
  const requests = useResource('/requests',refreshKey);
  const refresh = () => setRefreshKey(value => value + 1);
  useEffect(() => { const change = () => { const next=location.hash.slice(1); setPage(paths.includes(next) ? next : 'overview'); setMenuOpen(false); }; window.addEventListener('hashchange',change); return () => window.removeEventListener('hashchange',change); }, []);
  useEffect(() => {let active=true; api('/health').then(() => {if(active)setStatus('Services connected');}).catch(() => {if(active)setStatus('Services unavailable');}); return () => {active=false;};}, [refreshKey]);
  const go = destination => {location.hash=destination; setPage(destination);setMenuOpen(false); window.scrollTo({top:0,behavior:'smooth'});};
  const request = item => {setRole('NGO');setSelectedFood(item);go('requests');};
  const count=food.data?.filter(available).length;
  const locations=food.data ? new Set(food.data.filter(available).map(item=>item.location).filter(Boolean)).size : null;
  return <div className="app"><aside className={`sidebar ${menuOpen ? 'open' : ''}`}><a href="#overview" className="brand"><span className="brand-icon" aria-hidden="true">↗</span><span>food<span className="brand-light">bridge</span><small>GOOD FOOD. GREATER GOOD.</small></span></a><div className="workspace-label">YOUR WORKSPACE</div><nav aria-label="Main navigation">{pages.map((label,index)=><a href={`#${paths[index]}`} key={label} aria-current={page===paths[index]?'page':undefined} onClick={()=>setMenuOpen(false)} className={page===paths[index]?'selected':''}><span aria-hidden="true">{symbols[index]}</span>{label}{page===paths[index]&&<span className="nav-dot"/>}</a>)}</nav><div className="sidebar-bottom"><div className="side-message"><span aria-hidden="true">♧</span><h3>Small acts.<br/>Fuller plates.</h3><p>Your surplus can be someone’s next meal.</p><button onClick={()=>go('share')}>Share food <span aria-hidden="true">↗</span></button></div><a className="docs-link" href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">API documentation ↗</a><div className="version">FOOD BRIDGE / COMMUNITY FIRST</div></div></aside>
    <div className="main-wrap"><header className="topbar"><div className="breadcrumb"><button className="mobile-menu" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={()=>setMenuOpen(!menuOpen)}>☰</button><span>Workspace</span><span>/</span><strong>{pages[paths.indexOf(page)]}</strong></div><div className="top-actions"><span className={`api-status ${status==='Services connected'?'online':''}`}><i/>{status}</span><label className="role-select"><span>View as</span><select aria-label="Workspace role (not authentication)" value={role} onChange={e=>setRole(e.target.value)}><option value="NGO">NGO</option><option value="DONOR">Donor</option></select></label><div className="avatar" aria-hidden="true">{role==='NGO'?'N':'D'}</div></div></header>
    <main><div className="page-heading"><div><span className="eyebrow">LESS WASTE. MORE POSSIBILITY.</span><h1>{({overview:'A little surplus. A lot of good.',food:'Find food. Feed possibility.',share:'Good food deserves a second chance.',requests:'Bring good food closer.',reviews:'Stories from the table.'})[page]}</h1><p>{({overview:'Connect good food with the people who need it. Every donation matters.',food:'Discover surplus food shared by donors in your community.',share:'Turn what you have into something your community needs.',requests:'Request, reserve, and record each community handoff.',reviews:'Real experiences. Better donations. A stronger community.'})[page]}</p></div>{['overview','food'].includes(page)&&<button className="button primary" onClick={()=>go('share')}><span aria-hidden="true">＋</span> Share food</button>}</div>
    {page==='overview'&&<><section className="hero"><div className="hero-copy"><span className="hero-tag"><i/> A BRIDGE TO A BETTER TOMORROW</span><h2>More sharing.<br/>Less going to waste.</h2><p>Bring surplus food to the right table.<br/>One connection can make a meaningful difference.</p><button className="button cream" onClick={()=>go('food')}>Explore available food <span aria-hidden="true">↗</span></button></div><div className="hero-art" aria-hidden="true"><svg viewBox="0 0 400 300"><ellipse cx="206" cy="258" rx="144" ry="16" fill="#153e30"/><path d="M90 136h232l-23 116H113z" fill="#d2b082"/><path d="M112 142h188l-13 94H124z" fill="#e7c89f"/><path d="M119 139 89 89l30-21 46 71" fill="#ecd6a7"/><path d="m127 135-25-53m38 51-20-45" stroke="#bd9d6d" strokeWidth="5"/><ellipse cx="195" cy="108" rx="39" ry="46" fill="#73996b"/><path d="m189 134 10-56m-8 30-18-16m20 4 19-15" stroke="#c4d1a2" strokeWidth="4" fill="none"/><path d="M245 135c-20-17-14-48 2-56 11-6 18 1 20 11 15-12 33-1 30 16-3 18-23 28-52 29" fill="#e5a25c"/><path d="m260 85 8-19m-6 19-10-17" stroke="#a6b17b" strokeWidth="6"/><path d="M144 150c-7-37 30-48 45-19 7-39 43-36 51-7 28-29 64-6 53 26" fill="#abc08b"/><path d="M90 136h232v19H90z" fill="#efdab5"/><path d="M185 185c10-18 32-18 42 0-7 17-15 26-21 30-8-5-17-16-21-30" fill="#63846b"/><path d="M91 154h230M121 175h43m72 0h59" stroke="#b58e5f" strokeWidth="3"/><path d="m52 89 8-15m-18 8 17 5m280 89 16-9m-10 22 7-15" stroke="#97b79b" strokeWidth="3" strokeLinecap="round"/></svg><span className="art-caption">a little kindness goes a long way</span></div></section><div className="stats"><article><div className="stat-icon">◉</div><div><span>Available listings</span><strong>{count??'—'}</strong><small>Ready for a new table</small></div></article><article><div className="stat-icon sand">⌖</div><div><span>Pickup locations</span><strong>{locations??'—'}</strong><small>From available food listings</small></div></article><article><div className="stat-icon">⇄</div><div><span>Pending requests</span><strong>{requests.data?.filter(row => row.status === 'PENDING').length ?? '—'}</strong><small>Waiting for a donor decision</small></div></article><article><div className="stat-icon sand">✓</div><div><span>Completed collections</span><strong>{requests.data?.filter(row => row.status === 'COMPLETED').length ?? '—'}</strong><small>Food shared with the community</small></div></article></div><div className="section-header"><div><span className="eyebrow">FRESH OPPORTUNITIES</span><h2>Ready to make a difference</h2></div><button className="text-button" onClick={()=>go('food')}>View all food <span aria-hidden="true">→</span></button></div><FoodList resource={food} onRequest={request} retry={refresh} limit={3}/></>}
    {page==='food'&&<FoodList resource={food} onRequest={request} retry={refresh} filters/>}
    {page==='share'&&<ShareFood refresh={refresh}/>}
    {page==='requests'&&<Requests selectedFood={selectedFood} refresh={refresh} role={role} refreshKey={refreshKey} foodResource={food} requestResource={requests}/>}
    {page==='reviews'&&<Reviews refreshKey={refreshKey} refresh={refresh} foodResource={food}/>}
    <footer><span>foodbridge <span className="muted">· Built around community.</span></span><span>Local demo · Role selection is not sign-in</span></footer></main></div></div>;
}
