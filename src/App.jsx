// src/App.jsx
import React, { useEffect, useState } from "react";
import {
  Truck,
  Bus,
  MapPin,
  Package,
  ShieldCheck,
  Clock3,
  Menu,
  X,
  ArrowRight,
  Phone,
  Mail,
  Globe2,
  Search,
  Send,
  MessageSquareText,
  Lock,
  LogOut,
} from "lucide-react";

const services = [
  { icon: Bus, title: "Passenger Transport", desc: "Convenient passenger travel with route information, trip enquiries and booking support." },
  { icon: Truck, title: "Goods and Cargo Haulage", desc: "Reliable movement of commercial goods, consignments and general cargo." },
  { icon: Globe2, title: "Cross-Border Logistics", desc: "Transport coordination for journeys between Kenya and neighbouring East African countries." },
  { icon: Package, title: "Parcel and Delivery", desc: "Collection and delivery coordination for parcels and business consignments." },
];

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

const defaultForm = {
  fullName: "",
  phoneNumber: "",
  pickupLocation: "",
  destination: "",
  typeOfGoods: "",
  estimatedWeight: "",
  travelDate: "",
  numberOfPassengers: "",
  additionalDetails: "",
};

const statusOptions = ["NEW", "CONTACTED", "QUOTED", "IN_PROGRESS", "COMPLETED", "CANCELLED"];

function App() {
  const [route, setRoute] = useState(window.location.hash === "#admin" ? "admin" : "public");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const syncRoute = () => setRoute(window.location.hash === "#admin" ? "admin" : "public");
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  return (
    <>
      <SiteHeader route={route} setRoute={setRoute} menuOpen={menuOpen} setMenuOpen={setMenuOpen} />
      {route === "admin" ? <AdminDashboard /> : <PublicWebsite />}
    </>
  );
}

function SiteHeader({ route, setRoute, menuOpen, setMenuOpen }) {
  const closeMenu = () => setMenuOpen(false);
  const navigateToView = nextRoute => {
    window.location.hash = nextRoute === "admin" ? "#admin" : "";
    setRoute(nextRoute);
    closeMenu();
  };

  return (
    <header className="header">
      <a className="brand" href="#home" onClick={closeMenu}>
        <img src="/dextere-logo.jpg" alt="Dextere Haulers Limited logo" />
        <span><b>DEXTERE HAULERS</b><small>LIMITED · TRANSPORT & LOGISTICS</small></span>
      </a>
      <button className="menuBtn" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">
        {menuOpen ? <X /> : <Menu />}
      </button>
      <nav className={menuOpen ? "nav open" : "nav"} aria-label="Main navigation">
        <a href="#home" onClick={closeMenu}>Home</a>
        <a href="#services" onClick={closeMenu}>Services</a>
        <a href="#coverage" onClick={closeMenu}>Coverage</a>
        <a href="#tracking" onClick={closeMenu}>Track Shipment</a>
        <div className="viewToggle" role="group" aria-label="Choose a view">
          <button type="button" className={`viewToggleTab ${route === "public" ? "selected" : ""}`} aria-current={route === "public" ? "page" : undefined} onClick={() => navigateToView("public")}>Customer Tracking Portal</button>
          <button type="button" className={`viewToggleTab ${route === "admin" ? "selected" : ""}`} aria-current={route === "admin" ? "page" : undefined} onClick={() => navigateToView("admin")}>Dispatcher Admin</button>
        </div>
        <a href="#booking" className="navCta" onClick={closeMenu}>Request a Quote</a>
      </nav>
    </header>
  );
}

function PublicWebsite() {
  const [bookingType, setBookingType] = useState("Goods / Cargo");
  const [formData, setFormData] = useState(defaultForm);
  const [formMessage, setFormMessage] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  // Tracking state
  const [trackingId, setTrackingId] = useState("");
  const [trackingData, setTrackingData] = useState(null);
  const [trackingError, setTrackingError] = useState("");
  const [trackingLoading, setTrackingLoading] = useState(false);

  const updateField = (field, value) => setFormData(prev => ({ ...prev, [field]: value }));
  const resetForm = () => {
    setFormData(defaultForm);
    setBookingType("Goods / Cargo");
  };

  const formatErrorMessage = errors => {
    if (!errors) return "Unable to submit enquiry right now.";
    if (typeof errors === "string") return errors;
    if (Array.isArray(errors)) return errors.join(" ");
    if (typeof errors === "object") {
      const values = Object.values(errors).flatMap(v => (Array.isArray(v) ? v : [v]));
      const msgs = values.map(v => (typeof v === "string" ? v : v.detail || v.message || "Invalid value"));
      return msgs.join(" ");
    }
    return "Unable to submit enquiry right now.";
  };

  const handleBooking = async event => {
    event.preventDefault();
    setLoading(true);
    setFormMessage({ type: "", text: "" });

    const payload = {
      full_name: formData.fullName.trim(),
      phone_number: formData.phoneNumber.trim(),
      pickup_location: formData.pickupLocation.trim(),
      destination: formData.destination.trim(),
      transport_category: bookingType,
      type_of_goods: formData.typeOfGoods.trim(),
      estimated_weight: formData.estimatedWeight.trim(),
      travel_date: formData.travelDate || null,
      number_of_passengers: formData.numberOfPassengers ? Number(formData.numberOfPassengers) : null,
      additional_details: formData.additionalDetails.trim(),
    };

    if (!payload.full_name || !payload.phone_number || !payload.pickup_location || !payload.destination) {
      setFormMessage({ type: "error", text: "Please complete all required customer details before submitting." });
      setLoading(false);
      return;
    }
    if (bookingType === "Goods / Cargo" && (!payload.type_of_goods || !payload.estimated_weight)) {
      setFormMessage({ type: "error", text: "Type of goods and estimated weight are required for a Goods / Cargo enquiry." });
      setLoading(false);
      return;
    }
    if (bookingType === "Passenger" && (!payload.travel_date || payload.number_of_passengers === null || Number(payload.number_of_passengers) < 1)) {
      setFormMessage({ type: "error", text: "Travel date and number of passengers are required for a Passenger enquiry." });
      setLoading(false);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/public/enquiries/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(formatErrorMessage(data?.errors || data?.message || data));
      setSent(true);
      setFormMessage({ type: "success", text: `Your enquiry was submitted successfully. Reference: ${data?.enquiry?.reference_number || "DEX-NEW"}` });
      resetForm();
    } catch (error) {
      setSent(false);
      setFormMessage({ type: "error", text: error.message || "Unable to submit enquiry right now. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const handleTrackingSearch = async e => {
    e.preventDefault();
    if (!trackingId) {
      setTrackingError("Please enter a tracking ID.");
      return;
    }
    setTrackingLoading(true);
    setTrackingError("");
    setTrackingData(null);
    try {
      const response = await fetch(`${API_BASE}/public/track/${trackingId.trim()}/`);
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || data?.message || "Tracking lookup failed.");
      setTrackingData(data);
    } catch (err) {
      setTrackingError(err.message || "Unable to retrieve tracking information.");
    } finally {
      setTrackingLoading(false);
    }
  };

  return (
    <div>
      <main>
        {/* Hero */}
        <section className="hero" id="home">
          <div className="heroShade" />
          <div className="heroContent">
            <p className="eyebrow"><span /> KENYA · EAST AFRICA · BEYOND</p>
            <h1>Moving people.<br /><em>Delivering possibilities.</em></h1>
            <p className="heroText">Dependable passenger transport and goods haulage, connecting destinations across Kenya and beyond its borders.</p>
            <div className="heroActions">
              <a className="btn primary" href="#booking">Book / Request a Quote <ArrowRight size={18} /></a>
              <a className="btn outline" href="#services">Explore Services</a>
            </div>
            <div className="heroTrust">
              <span><ShieldCheck /> Safety-minded service</span>
              <span><MapPin /> Nationwide coverage</span>
              <span><Clock3 /> Reliable coordination</span>
            </div>
          </div>
        </section>

        {/* Quick strip */}
        <section className="quickStrip">
          <div><b>47</b><span>Counties in Kenya</span></div>
          <div><b>2</b><span>Core transport services</span></div>
          <div><b>EA</b><span>Regional connections</span></div>
          <div><b>24/7</b><span>Enquiry access online</span></div>
        </section>

        {/* Services */}
        <section className="section" id="services">
          <div className="sectionHead">
            <p className="eyebrow green">WHAT WE DO</p>
            <h2>Transport solutions built around your journey.</h2>
            <p>From passenger movement to commercial cargo, Dextere Haulers Limited helps connect people, businesses and destinations.</p>
          </div>
          <div className="serviceGrid">
            {services.map(({ icon: Icon, title, desc }) => (
              <article className="serviceCard" key={title}>
                <div className="serviceIcon"><Icon /></div>
                <h3>{title}</h3>
                <p>{desc}</p>
                <a href="#booking">Make an enquiry <ArrowRight size={16} /></a>
              </article>
            ))}
          </div>
        </section>

        {/* Coverage */}
        <section className="coverage" id="coverage">
          <div className="coverageText">
            <p className="eyebrow">OUR NETWORK</p>
            <h2>From local routes to cross-border journeys.</h2>
            <p>Plan transport within Kenya's 47 counties and enquire about regional routes connecting Kenya with neighbouring countries, subject to route availability, permits and operational arrangements.</p>
            <div className="countryTags">
              <span>Kenya</span><span>Uganda</span><span>Tanzania</span><span>Rwanda</span><span>South Sudan</span><span>Ethiopia</span>
            </div>
            <a className="btn light" href="#booking">Ask about your route <ArrowRight size={18} /></a>
          </div>
          <div className="coverageVisual">
            <div className="routeCircle"><Globe2 size={76} /><b>KENYA</b><small>Connecting East Africa</small></div>
            <div className="routeLine line1" />
            <div className="routeLine line2" />
            <div className="routeLine line3" />
            <span className="pin pin1">Nairobi</span>
            <span className="pin pin2">Mombasa</span>
            <span className="pin pin3">Border routes</span>
          </div>
        </section>

        {/* Tracking */}
        <section className="section splitSection" id="tracking">
          <div>
            <p className="eyebrow green">SHIPMENT UPDATES</p>
            <h2>Track your consignment.</h2>
            <p>Enter the reference number provided after your booking. Online tracking will become active once the company's shipment database and status‑update process are connected.</p>
          </div>
          <form className="trackBox contentCard" onSubmit={handleTrackingSearch}>
            <label htmlFor="trackingId">Tracking ID</label>
            <div className="trackInput">
              <Search />
              <input id="trackingId" value={trackingId} onChange={e => setTrackingId(e.target.value)} placeholder="e.g. DX-9021" />
              <button type="submit" aria-label="Search tracking number"><ArrowRight /></button>
            </div>
            {trackingLoading && <p className="formNote">Loading...</p>}
            {trackingError && <p className="errorNote">{trackingError}</p>}
            {trackingData && (
              <div className="trackingCard">
                <h3>Shipment Status</h3>
                <p><strong>Tracking ID:</strong> {trackingData.tracking_id}</p>
                <p><strong>Route:</strong> {trackingData.origin_city} → {trackingData.destination_city}</p>
                <p><strong>Sender:</strong> {trackingData.sender}</p>
                <p><strong>Receiver:</strong> {trackingData.receiver}</p>
                <p><strong>Cargo:</strong> {trackingData.cargo_details}</p>
                <p><strong>Vehicle / Driver:</strong> {trackingData.vehicle_driver}</p>
                <p><strong>Status:</strong> {trackingData.status}</p>
              </div>
            )}
          </form>
        </section>

        {/* Booking */}
        <section className="bookingSection" id="booking">
          <div className="bookingIntro">
            <p className="eyebrow">LET'S GET MOVING</p>
            <h2>Tell us what you need to move.</h2>
            <p>Send a booking enquiry or request a quotation. Our team can follow up to confirm availability, pricing and trip details.</p>
            <div className="contactLine"><Phone /> <span>Phone: +254 701 429 096 | +254 102 122 122 </span></div>
            <div className="contactLine"><Mail /> <span>Email: dexterlogistics33@gmail.com or Neo2herald@gmail.com</span></div>
          </div>
          <form className="bookingForm contentCard" onSubmit={handleBooking}>
            <div className="formTitle">Transport enquiry</div>
            <div className="typeSwitch">
              <button type="button" className={bookingType === "Goods / Cargo" ? "selected" : ""} onClick={() => setBookingType("Goods / Cargo")}>Goods / Cargo</button>
              <button type="button" className={bookingType === "Passenger" ? "selected" : ""} onClick={() => setBookingType("Passenger")}>Passenger</button>
            </div>
            <div className="formGrid">
              <label>Full name<input required value={formData.fullName} onChange={e => updateField("fullName", e.target.value)} placeholder="Your name" /></label>
              <label>Phone number<input required type="tel" value={formData.phoneNumber} onChange={e => updateField("phoneNumber", e.target.value)} placeholder="+254..." /></label>
              <label>Pickup location<input required value={formData.pickupLocation} onChange={e => updateField("pickupLocation", e.target.value)} placeholder="Town / County" /></label>
              <label>Destination<input required value={formData.destination} onChange={e => updateField("destination", e.target.value)} placeholder="Town / Country" /></label>
              {bookingType === "Goods / Cargo" ? (
                <>
                  <label>Type of goods<input value={formData.typeOfGoods} onChange={e => updateField("typeOfGoods", e.target.value)} placeholder="Describe the cargo" /></label>
                  <label>Estimated weight<input value={formData.estimatedWeight} onChange={e => updateField("estimatedWeight", e.target.value)} placeholder="e.g. 2 tonnes" /></label>
                </>
              ) : (
                <>
                  <label>Travel date<input type="date" value={formData.travelDate} onChange={e => updateField("travelDate", e.target.value)} /></label>
                  <label>Number of passengers<input type="number" min="1" value={formData.numberOfPassengers} onChange={e => updateField("numberOfPassengers", e.target.value)} placeholder="e.g. 2" /></label>
                </>
              )}
            </div>
            <label>Additional details<textarea rows="3" value={formData.additionalDetails} onChange={e => updateField("additionalDetails", e.target.value)} placeholder="Preferred date, cargo details, route or other requirements" /></label>
            <button className="btn primary submitBtn" type="submit" disabled={loading}>{loading ? "Sending..." : "Send enquiry"} <Send size={17} /></button>
            {formMessage.text && <p className={formMessage.type === "success" ? "successNote" : "errorNote"}>{formMessage.text}</p>}
            {sent && <p className="successNote">Your enquiry has been received and will be reviewed by the Dextere team.</p>}
          </form>
        </section>
      </main>

      <footer>
        <div className="footerBrand">
          <img src="/dextere-logo.jpg" alt="Dextere Haulers Limited" />
          <div><b>DEXTERE HAULERS LIMITED</b><small>Connecting Kenya. Delivering Beyond Borders.</small></div>
        </div>
        <p>Passenger transport · Goods haulage · Cross‑border logistics</p>
        <div className="footerBottom">
          <span>© {new Date().getFullYear()} Dextere Haulers Limited. All rights reserved.</span>
          <a href="#admin" className="adminLink">Admin Dashboard</a>
        </div>
      </footer>
    </div>
  );
}

function AdminDashboard() {
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total: 0, unread: 0, new: 0, completed: 0 });
  const [enquiries, setEnquiries] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  useEffect(() => {
    localStorage.removeItem("dextere_admin_token");
    localStorage.removeItem("dextere_admin_user");
  }, []);

  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data?.message || data?.detail || "Request failed.");
      if (response.status === 401 || response.status === 403) {
        setIsAdminLoggedIn(false);
        setToken("");
        setUsername("");
        setPassword("");
        setEnquiries([]);
        setStats({ total: 0, unread: 0, new: 0, completed: 0 });
        setSelectedId(null);
      }
      throw error;
    }
    return data;
  };

  const loadDashboard = async () => {
    if (!token) return;
    try {
      const query = new URLSearchParams({ search, status: statusFilter, category: categoryFilter }).toString();
      const [statsData, enquiriesData] = await Promise.all([
        fetchJson(`${API_BASE}/admin/stats/`),
        fetchJson(`${API_BASE}/admin/enquiries/?${query}`),
      ]);
      setStats(statsData || {});
      setEnquiries(Array.isArray(enquiriesData) ? enquiriesData : []);
      if (!selectedId && enquiriesData.length > 0) setSelectedId(enquiriesData[0].id);
    } catch (error) {
      setLoginError(error.message || "Unable to load dashboard data.");
    }
  };

  useEffect(() => { if (isAdminLoggedIn && token) loadDashboard(); }, [isAdminLoggedIn, token, search, statusFilter, categoryFilter]);

  const handleLogin = async e => {
    e.preventDefault();
    setLoading(true);
    setLoginError("");
    try {
      const response = await fetch(`${API_BASE}/admin/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const errors = data?.errors;
        const messages = errors && typeof errors === "object" && !Array.isArray(errors)
          ? Object.values(errors).flatMap(value => Array.isArray(value) ? value : [value])
          : [];
        const message = Array.isArray(errors)
          ? errors.join(" ")
          : typeof errors === "string"
            ? errors
            : messages.length
              ? messages.join(" ")
              : data?.message;
        throw new Error(message || "Login failed.");
      }
      if (!data?.user?.is_superuser || !data?.tokens?.access) {
        throw new Error("This account is not authorized to access the dispatcher dashboard.");
      }
      setUsername(data.user.username);
      setPassword("");
      setToken(data.tokens.access);
      setIsAdminLoggedIn(true);
    } catch (error) {
      setLoginError(error.message || "Unable to log in.");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setIsAdminLoggedIn(false);
    setToken("");
    setUsername("");
    setPassword("");
    setSelectedId(null);
    setEnquiries([]);
    setStats({ total: 0, unread: 0, new: 0, completed: 0 });
    setLoginError("");
    localStorage.removeItem("dextere_admin_token");
    localStorage.removeItem("dextere_admin_user");
  };

  const selectedEnquiry = enquiries.find(item => item.id === selectedId) || null;

  const handleStatusUpdate = async () => {
    if (!selectedEnquiry) return;
    try {
      const updated = await fetchJson(`${API_BASE}/admin/enquiries/${selectedEnquiry.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ status: selectedEnquiry.status }),
      });
      setEnquiries(prev => prev.map(item => item.id === updated.id ? updated : item));
      setSelectedId(updated.id);
    } catch (error) {
      setLoginError(error.message || "Status update failed.");
    }
  };

  const handleNoteUpdate = async () => {
    if (!selectedEnquiry) return;
    try {
      const updated = await fetchJson(`${API_BASE}/admin/enquiries/${selectedEnquiry.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ admin_notes: selectedEnquiry.admin_notes || "" }),
      });
      setEnquiries(prev => prev.map(item => item.id === updated.id ? updated : item));
      setSelectedId(updated.id);
    } catch (error) {
      setLoginError(error.message || "Note update failed.");
    }
  };

  const handleDelete = async () => {
    if (!selectedEnquiry) return;
    if (!window.confirm("Delete this enquiry permanently?")) return;
    try {
      await fetchJson(`${API_BASE}/admin/enquiries/${selectedEnquiry.id}/`, { method: "DELETE" });
      const next = enquiries.filter(item => item.id !== selectedEnquiry.id);
      setEnquiries(next);
      setSelectedId(next[0]?.id || null);
    } catch (error) {
      setLoginError(error.message || "Delete failed.");
    }
  };

  const openWhatsApp = phone => {
    const digits = (phone || "").replace(/\D/g, "");
    if (!digits) return;
    window.open(`https://wa.me/${digits}`, "_blank", "noopener,noreferrer");
  };

  if (!isAdminLoggedIn) {
    return (
      <div className="adminLoginShell">
        <form className="adminLoginCard contentCard" onSubmit={handleLogin}>
          <Lock size={30} aria-hidden="true" />
          <div className="adminBadge">Dextere Haulers</div>
          <h2>Dispatcher Admin</h2>
          <p>Sign in with your superadmin account to manage transport enquiries.</p>
          <label>Username<input autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)} /></label>
          <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
          {loginError && <p className="adminError">{loginError}</p>}
          <button className="btn primary" type="submit" disabled={loading}>{loading ? "Signing in..." : "Log in"}</button>
          <a href="#" className="returnLink" onClick={e => { e.preventDefault(); window.location.hash = ""; }}>Return to website</a>
        </form>
      </div>
    );
  }

  return (
    <div className="adminShell">
      <header className="adminHeader">
        <div>
          <div className="adminBadge">DEXTERE ADMIN</div>
          <h2>Transport Enquiries</h2>
        </div>
        <div className="adminHeaderActions">
          <span>Welcome, {username}</span>
          <button className="btn outline dark" onClick={logout} type="button"><LogOut size={16} /> Logout</button>
        </div>
      </header>
      <div className="adminStatsGrid">
        <div className="adminStat contentCard"><span>Total</span><strong>{stats.total || enquiries.length}</strong></div>
        <div className="adminStat contentCard"><span>New</span><strong>{stats.new || 0}</strong></div>
        <div className="adminStat contentCard"><span>Unread</span><strong>{stats.unread || 0}</strong></div>
        <div className="adminStat contentCard"><span>Completed</span><strong>{stats.completed || 0}</strong></div>
      </div>
      <main className="adminWorkspace">
        <aside className="adminSidebar contentCard">
          <div className="adminFilters">
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by customer or phone" />
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              {statusOptions.map(status => (<option key={status} value={status}>{status.replace("_", " ")}</option>))}
            </select>
            <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
              <option value="">All categories</option>
              <option value="Goods / Cargo">Goods / Cargo</option>
              <option value="Passenger">Passenger</option>
            </select>
          </div>
          <div className="adminList">
            {enquiries.length === 0 ? <div className="emptyState">No enquiries found.</div> : enquiries.map(enquiry => (
              <button key={enquiry.id} type="button" className={selectedId === enquiry.id ? "adminListItem selected" : "adminListItem"} onClick={() => setSelectedId(enquiry.id)}>
                <div className="listTopRow"><span>{enquiry.reference_number}</span>{enquiry.is_unread && <span className="badge">New</span>}</div>
                <strong>{enquiry.full_name}</strong>
                <small>{enquiry.phone_number}</small>
                <span>{enquiry.transport_category}</span>
                <div className="listMeta"><span>{enquiry.status}</span><span>{new Date(enquiry.submitted_at).toLocaleDateString()}</span></div>
              </button>
            ))}
          </div>
        </aside>
        <section className="adminDetail contentCard">
          {!selectedEnquiry ? (
            <div className="emptyState large">Select an enquiry to review details.</div>
          ) : (
            <>
              <div className="detailHeader">
                <div>
                  <div className="adminBadge">{selectedEnquiry.reference_number}</div>
                  <h3>{selectedEnquiry.full_name}</h3>
                </div>
                <div className="detailActions">
                  <button className="btn outline dark" type="button" onClick={() => openWhatsApp(selectedEnquiry.phone_number)}><MessageSquareText size={15} /> WhatsApp</button>
                  <a href={`tel:${selectedEnquiry.phone_number}`} className="btn outline dark" type="button">Call</a>
                  <button className="btn danger" type="button" onClick={handleDelete}>Delete</button>
                </div>
              </div>
              <div className="detailGrid">
                <div><span>Category</span><strong>{selectedEnquiry.transport_category}</strong></div>
                <div><span>Phone</span><strong>{selectedEnquiry.phone_number}</strong></div>
                <div><span>Pickup</span><strong>{selectedEnquiry.pickup_location}</strong></div>
                <div><span>Destination</span><strong>{selectedEnquiry.destination}</strong></div>
                <div><span>Type of goods</span><strong>{selectedEnquiry.type_of_goods || "—"}</strong></div>
                <div><span>Estimated weight</span><strong>{selectedEnquiry.estimated_weight || "—"}</strong></div>
                <div><span>Travel date</span><strong>{selectedEnquiry.travel_date ? new Date(selectedEnquiry.travel_date).toLocaleDateString() : "—"}</strong></div>
                <div><span>Passengers</span><strong>{selectedEnquiry.number_of_passengers ?? "—"}</strong></div>
                <div className="fullWidth"><span>Additional details</span><strong>{selectedEnquiry.additional_details || "No additional details provided."}</strong></div>
              </div>
              <div className="statusBlock">
                <label>
                  Update status
                  <select value={selectedEnquiry.status} onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, status: e.target.value } : item))}>
                    {statusOptions.map(status => (<option key={status} value={status}>{status.replace("_", " ")}</option>))}
                  </select>
                </label>
                <button className="btn primary" type="button" onClick={handleStatusUpdate}>Save status</button>
              </div>
              <div className="notesBlock">
                <label>
                  Admin notes
                  <textarea value={selectedEnquiry.admin_notes || ""} onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, admin_notes: e.target.value } : item))} rows="5" placeholder="Add private notes for the client follow‑up" />
                </label>
                <button className="btn primary" type="button" onClick={handleNoteUpdate}>Save notes</button>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
