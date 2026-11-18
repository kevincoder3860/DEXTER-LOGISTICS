// src/App.jsx
import React, { useEffect, useState } from "react";
import "./mpesa.css";
import {
  Truck,
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
  Copy,
  Check,
  CalendarClock,
  Navigation,
  MessageCircle,
} from "lucide-react";

const services = [
  { icon: Truck, title: "Goods and Cargo Haulage", desc: "Reliable movement of commercial goods, consignments and general cargo." },
  { icon: Globe2, title: "Cross-Border Logistics", desc: "Transport coordination for journeys between Kenya and neighbouring East African countries." },
  { icon: Package, title: "Parcel and Delivery", desc: "Collection and delivery coordination for parcels and business consignments." },
];

const configuredApiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const API_BASE = `${(/^https?:\/\//i.test(configuredApiUrl) ? configuredApiUrl : `https://${configuredApiUrl}`).replace(/\/+$/, "")}/api`;

const defaultForm = {
  fullName: "",
  email: "",
  phoneNumber: "",
  pickupLocation: "",
  destination: "",
  typeOfGoods: "",
  estimatedWeight: "",
  additionalDetails: "",
};

const statusOptions = ["NEW", "CONTACTED", "QUOTED", "QUOTE_CONFIRMED", "APPROVED", "IN_PROGRESS", "COMPLETED", "CANCELLED"];

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
  const navigateToView = (nextRoute, event) => {
    event?.preventDefault();
    window.location.hash = nextRoute === "admin" ? "#admin" : "";
    setRoute(nextRoute);
    closeMenu();
    if (nextRoute === "public") {
      requestAnimationFrame(() => {
        document.getElementById("tracking")?.scrollIntoView({ behavior: "smooth" });
      });
    }
  };

  return (
    <header className="header">
      <a className="brand" href="#home" onClick={closeMenu}>
        <img src="/dextere-logo.jpg" alt="Dexter Haulers Limited logo" />
        <span><b>DEXTER HAULERS</b><small>LIMITED · TRANSPORT & LOGISTICS</small></span>
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
          <a href="#tracking" className={`viewToggleTab ${route === "public" ? "selected" : ""}`} aria-current={route === "public" ? "page" : undefined} onClick={event => navigateToView("public", event)}>Customer Tracking Portal</a>
          <button type="button" className={`viewToggleTab ${route === "admin" ? "selected" : ""}`} aria-current={route === "admin" ? "page" : undefined} onClick={event => navigateToView("admin", event)}>Dispatcher Admin</button>
        </div>
        <a href="#booking" className="navCta" onClick={closeMenu}>Request a Quote</a>
      </nav>
    </header>
  );
}

function PublicWebsite() {
  const [formData, setFormData] = useState(defaultForm);
  const [formMessage, setFormMessage] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [submittedReference, setSubmittedReference] = useState("");

  // Tracking state
  const [trackingId, setTrackingId] = useState("");
  const [trackingData, setTrackingData] = useState(null);
  const [trackingError, setTrackingError] = useState("");
  const [trackingLoading, setTrackingLoading] = useState(false);

  const updateField = (field, value) => setFormData(prev => ({ ...prev, [field]: value }));
  const resetForm = () => {
    setFormData(defaultForm);
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
    setSent(false);
    setSubmittedReference("");
    setFormMessage({ type: "", text: "" });

    const payload = {
      full_name: formData.fullName.trim(),
      email: formData.email.trim(),
      phone_number: formData.phoneNumber.trim(),
      pickup_location: formData.pickupLocation.trim(),
      destination: formData.destination.trim(),
      transport_category: "Goods / Cargo",
      type_of_goods: formData.typeOfGoods.trim(),
      estimated_weight: formData.estimatedWeight.trim(),
      additional_details: formData.additionalDetails.trim(),
    };

    if (!payload.full_name || !payload.email || !payload.phone_number || !payload.pickup_location || !payload.destination) {
      setFormMessage({ type: "error", text: "Please complete all required customer details before submitting." });
      setLoading(false);
      return;
    }
    if (!payload.type_of_goods || !payload.estimated_weight) {
      setFormMessage({ type: "error", text: "Type of goods and estimated weight are required for a Goods / Cargo enquiry." });
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
      const reference = data?.enquiry?.reference_number;
      if (!reference) throw new Error("Your enquiry was submitted, but no tracking reference was returned. Please contact our team.");
      setSent(true);
      setSubmittedReference(reference);
      setFormMessage({ type: "success", text: "Your enquiry was submitted successfully." });
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
            <h1>Moving freight.<br /><em>Delivering possibilities.</em></h1>
            <p className="heroText">Dependable goods haulage and freight logistics, connecting destinations across Kenya and beyond its borders.</p>
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
            <p>From commercial cargo to regional freight, Dexter Haulers Limited helps businesses and destinations stay connected.</p>
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
            <p>Enter the reference number provided after your booking to check your quote and payment status.</p>
          </div>
          <form className="trackBox contentCard" onSubmit={handleTrackingSearch}>
            <label htmlFor="trackingId">Tracking ID</label>
            <div className="trackInput">
              <Search />
              <input id="trackingId" value={trackingId} onChange={e => setTrackingId(e.target.value)} placeholder="e.g. DRX-20261113-A1B2" />
              <button type="submit" aria-label="Search tracking number"><ArrowRight /></button>
            </div>
            {trackingLoading && <p className="formNote">Loading...</p>}
            {trackingError && <p className="errorNote trackingError" role="alert">We couldn&apos;t find that shipment. Please check the Tracking ID and try again.</p>}
            {trackingData && (
              <ShipmentTrackingCard order={trackingData} />
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
            <div className="cargoLabel">Goods / Cargo</div>
            <div className="formGrid">
              <label>Full name<input required value={formData.fullName} onChange={e => updateField("fullName", e.target.value)} placeholder="Your name" /></label>
              <label>Email address<input required type="email" autoComplete="email" value={formData.email} onChange={e => updateField("email", e.target.value)} placeholder="you@example.com" /></label>
              <label>Phone number<input required type="tel" value={formData.phoneNumber} onChange={e => updateField("phoneNumber", e.target.value)} placeholder="+254..." /></label>
              <label>Pickup location<input required value={formData.pickupLocation} onChange={e => updateField("pickupLocation", e.target.value)} placeholder="Town / County" /></label>
              <label>Destination<input required value={formData.destination} onChange={e => updateField("destination", e.target.value)} placeholder="Town / Country" /></label>
              <label>Type of goods<input required value={formData.typeOfGoods} onChange={e => updateField("typeOfGoods", e.target.value)} placeholder="Describe the cargo" /></label>
              <label>Estimated weight<input required value={formData.estimatedWeight} onChange={e => updateField("estimatedWeight", e.target.value)} placeholder="e.g. 2 tonnes" /></label>
            </div>
            <label>Additional details<textarea rows="3" value={formData.additionalDetails} onChange={e => updateField("additionalDetails", e.target.value)} placeholder="Preferred date, cargo details, route or other requirements" /></label>
            <button className="btn primary submitBtn" type="submit" disabled={loading}>{loading ? "Sending..." : "Send enquiry"} <Send size={17} /></button>
            {formMessage.text && <p className={formMessage.type === "success" ? "successNote" : "errorNote"}>{formMessage.text}</p>}
            {sent && submittedReference && (
              <div className="referenceNotice" role="status" aria-live="polite">
                <strong>Quote tracking reference</strong>
                <code>{submittedReference}</code>
                <p>Please copy and keep your reference code safe to track the progress and status of your quote.</p>
                <a href="#tracking">Track your quote</a>
              </div>
            )}
          </form>
        </section>
      </main>

      <footer>
        <div className="footerBrand">
          <img src="/dextere-logo.jpg" alt="Dexter Haulers Limited" />
          <div><b>DEXTER HAULERS LIMITED</b><small>Connecting Kenya. Delivering Beyond Borders.</small></div>
        </div>
        <p>Goods haulage · Freight logistics · Cross‑border transport</p>
        <div className="footerBottom">
          <span>© {new Date().getFullYear()} Dexter Haulers Limited. All rights reserved.</span>
          <a href="#admin" className="adminLink">Admin Dashboard</a>
        </div>
      </footer>
    </div>
  );
}

function ShipmentTrackingCard({ order }) {
  const [copied, setCopied] = useState(false);

  const formatDate = value => {
    if (!value) return "To be confirmed";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "To be confirmed";
    return date.toLocaleString("en-KE", { dateStyle: "medium", timeStyle: "short" });
  };

  const copyTrackingId = async () => {
    try {
      await navigator.clipboard.writeText(order.reference_number);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  const statusMap = {
    NEW: "Quote Pending",
    CONTACTED: "Quote Pending",
    QUOTED: "Quote Pending",
    QUOTE_CONFIRMED: "Awaiting Payment",
    APPROVED: "Awaiting Payment",
    IN_PROGRESS: "In Transit",
    COMPLETED: "Delivered",
    CANCELLED: "Cancelled",
  };
  const statusLabel = statusMap[order.status] || order.status?.replace(/_/g, " ") || "Processing";

  const statusOrder = ["NEW", "CONTACTED", "QUOTED", "QUOTE_CONFIRMED", "APPROVED", "IN_PROGRESS", "COMPLETED"];
  const currentRank = statusOrder.indexOf(order.status);
  const quoteRank = statusOrder.indexOf("QUOTED");
  const paymentRank = statusOrder.indexOf("APPROVED");
  const transitRank = statusOrder.indexOf("IN_PROGRESS");
  const deliveredRank = statusOrder.indexOf("COMPLETED");
  const isPaid = order.payment_status === "PAID";

  const milestones = [
    {
      label: "Enquiry Received",
      detail: "Your shipment request was submitted",
      timestamp: order.submitted_at,
      complete: Boolean(order.submitted_at),
    },
    {
      label: "Quote Issued",
      detail: order.quoted_amount ? `Quoted at KES ${Number(order.quoted_amount).toLocaleString("en-KE")}` : "Awaiting dispatch quotation",
      timestamp: currentRank >= quoteRank ? order.updated_at : null,
      complete: currentRank >= quoteRank,
    },
    {
      label: "Payment Confirmed",
      detail: isPaid ? "Payment received" : "Payment pending",
      timestamp: isPaid ? order.updated_at : null,
      complete: isPaid,
    },
    {
      label: "In Transit",
      detail: order.current_checkpoint || "Dispatch will add your current checkpoint",
      timestamp: currentRank >= transitRank ? order.updated_at : null,
      complete: currentRank >= transitRank,
    },
    {
      label: "Delivered",
      detail: currentRank >= deliveredRank ? "Shipment completed" : "Awaiting final delivery",
      timestamp: currentRank >= deliveredRank ? order.updated_at : null,
      complete: currentRank >= deliveredRank,
    },
  ];

  const paymentDue = ["QUOTE_CONFIRMED", "APPROVED"].includes(order.status) && !isPaid;
  const amount = Number(order.quoted_amount);
  const dispatchMessage = encodeURIComponent(`Hello Dexter Dispatch, I need support with shipment ${order.reference_number}.`);
  const dispatchWhatsApp = `https://wa.me/254725674910?text=${dispatchMessage}`;

  return (
    <div className="trackingCard">
      <div className="shipmentHeader">
        <div>
          <span className="trackingLabel">Tracking ID</span>
          <div className="trackingReference">
            <strong>{order.reference_number}</strong>
            <button type="button" className="copyButton" onClick={copyTrackingId} aria-label="Copy tracking ID">
              {copied ? <Check size={15} /> : <Copy size={15} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
        <div className="shipmentHeaderMeta">
          <span className={`statusPill status-${String(order.status).toLowerCase().replace(/_/g, "-")}`}>{statusLabel}</span>
          <span className="etaText"><CalendarClock size={16} /> ETA: {formatDate(order.estimated_arrival)}</span>
        </div>
      </div>

      <div className="shipmentSummaryGrid">
        <div className="paymentSummary">
          <span>Quote Amount</span>
          <strong>{Number.isFinite(amount) && amount > 0 ? `KES ${amount.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "Quote pending"}</strong>
          <div className="paymentMeta">
            <span>Payment: <b className={isPaid ? "paidText" : ""}>{isPaid ? "Paid" : "Pending"}</b></span>
            {order.mpesa_receipt && <span>Receipt: <b>{order.mpesa_receipt}</b></span>}
          </div>
        </div>
        {paymentDue && <MpesaCheckout order={order} />}
      </div>

      <div className="shipmentDetailsGrid">
        <div><span>Origin</span><strong>{order.pickup_location || "—"}</strong></div>
        <div><span>Destination</span><strong>{order.destination || "—"}</strong></div>
        <div><span>Freight Category</span><strong>{order.transport_category || "Goods / Cargo"}</strong></div>
        <div><span>Cargo Description</span><strong>{order.type_of_goods || "—"}</strong></div>
        <div><span>Truck Registration</span><strong>{order.truck_registration || "Awaiting dispatch assignment"}</strong></div>
        <div>
          <span>Driver Contact</span>
          <strong>{order.driver_name ? `${order.driver_name} · ` : ""}{order.driver_phone || "Awaiting dispatch assignment"}</strong>
        </div>
      </div>

      <div className="timelineSection">
        <h3>Shipment Progress</h3>
        <div className="shipmentTimeline" aria-label="Shipment progress">
          {milestones.map(milestone => (
            <div className={`timelineItem ${milestone.complete ? "complete" : ""}`} key={milestone.label}>
              <div className="timelineMarker">{milestone.complete ? <Check size={14} /> : null}</div>
              <div className="timelineContent">
                <strong>{milestone.label}</strong>
                <span>{milestone.detail}</span>
                <time>{milestone.timestamp ? formatDate(milestone.timestamp) : "Pending"}</time>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="dispatchSupport">
        <div>
          <b>Need help with this shipment?</b>
          <span>Contact dispatch and include your Tracking ID.</span>
        </div>
        <div className="dispatchActions">
          <a className="supportButton" href="tel:+254725674910"><Phone size={16} /> Call Dispatch</a>
          <a className="supportButton whatsapp" href={dispatchWhatsApp} target="_blank" rel="noreferrer"><MessageCircle size={16} /> WhatsApp</a>
        </div>
      </div>
    </div>
  );
}

function MpesaCheckout({ order }) {
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("");
  const [paymentStarted, setPaymentStarted] = useState(false);
  const amount = Number(order.total_price);

  const handlePayment = async () => {
    if (!phone.trim()) {
      setMessage("Enter the M-Pesa phone number to continue.");
      setMessageType("error");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/payments/paystack-stk/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: order.id,
          phone_number: phone.trim(),
          amount,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.success) {
        throw new Error(data.message || "Unable to start M-Pesa payment.");
      }
      setMessage("Check your phone for the STK Push.");
      setMessageType("success");
      setPaymentStarted(true);
    } catch (error) {
      setMessage(error.message || "Unable to start M-Pesa payment. Please try again.");
      setMessageType("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mpesaCheckout">
      <h4>Pay your confirmed quote</h4>
      <p className="mpesaAmount">KES {amount.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
      <label htmlFor={`mpesa-phone-${order.id}`}>M-Pesa phone number</label>
      <input
        id={`mpesa-phone-${order.id}`}
        type="tel"
        value={phone}
        onChange={event => setPhone(event.target.value)}
        placeholder="0712345678"
        autoComplete="tel"
      />
      <button className="btn primary" type="button" onClick={handlePayment} disabled={loading || paymentStarted || !Number.isFinite(amount) || amount <= 0}>
        {loading ? "Sending STK Push..." : paymentStarted ? "STK Push sent" : `Pay KES ${amount.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} via M-Pesa`}
      </button>
      {message && <p className={messageType === "success" ? "successNote" : "errorNote"} role="status">{message}</p>}
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
        body: JSON.stringify({
          status: selectedEnquiry.status,
          quoted_amount: selectedEnquiry.quoted_amount || null,
          estimated_arrival: selectedEnquiry.estimated_arrival || null,
          truck_registration: selectedEnquiry.truck_registration || "",
          driver_name: selectedEnquiry.driver_name || "",
          driver_phone: selectedEnquiry.driver_phone || "",
          current_checkpoint: selectedEnquiry.current_checkpoint || "",
        }),
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

  const openWhatsApp = enquiry => {
    const digits = String(enquiry.phone_number || "").replace(/\D/g, "");
    const phone = digits.startsWith("0")
      ? `254${digits.slice(1)}`
      : digits.startsWith("254")
        ? digits
        : `254${digits}`;
    if (!/^254[17]\d{8}$/.test(phone)) {
      setLoginError("This enquiry does not have a valid Kenyan mobile number for WhatsApp.");
      return;
    }
    const message = `Hello, regarding your transport enquiry ${enquiry.reference_number}, we are following up on your quote. Please let us know if you have any questions.`;
    window.open(
      `https://wa.me/${phone}?text=${encodeURIComponent(message)}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  if (!isAdminLoggedIn) {
    return (
      <div className="adminLoginShell">
        <form className="adminLoginCard contentCard" onSubmit={handleLogin}>
          <Lock size={30} aria-hidden="true" />
          <div className="adminBadge">Dexter Haulers</div>
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
          <div className="adminBadge">DEXTER ADMIN</div>
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
                  <button className="btn outline dark" type="button" onClick={() => openWhatsApp(selectedEnquiry)}><MessageSquareText size={15} /> WhatsApp</button>
                  <a href={`tel:${selectedEnquiry.phone_number}`} className="btn outline dark" type="button">Call</a>
                  <button className="btn danger" type="button" onClick={handleDelete}>Delete</button>
                </div>
              </div>
              <div className="detailGrid">
                <div><span>Category</span><strong>{selectedEnquiry.transport_category}</strong></div>
                <div><span>Email</span><strong>{selectedEnquiry.email || "—"}</strong></div>
                <div><span>Phone</span><strong>{selectedEnquiry.phone_number}</strong></div>
                <div><span>Pickup</span><strong>{selectedEnquiry.pickup_location}</strong></div>
                <div><span>Destination</span><strong>{selectedEnquiry.destination}</strong></div>
                <div><span>Type of goods</span><strong>{selectedEnquiry.type_of_goods || "—"}</strong></div>
                <div><span>Estimated weight</span><strong>{selectedEnquiry.estimated_weight || "—"}</strong></div>
                <div className="fullWidth"><span>Additional details</span><strong>{selectedEnquiry.additional_details || "No additional details provided."}</strong></div>
                <div><span>Payment status</span><strong>{selectedEnquiry.payment_status || "PENDING"}</strong></div>
              </div>
              <div className="statusBlock">
                <label>
                  Confirmed quote amount (KES)
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={selectedEnquiry.quoted_amount ?? ""}
                    disabled={selectedEnquiry.payment_status === "PAID" || selectedEnquiry.payment_in_progress}
                    onChange={event => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, quoted_amount: event.target.value } : item))}
                    placeholder="Enter amount before confirming"
                  />
                </label>
                <label>
                  Update status
                  <select value={selectedEnquiry.status} onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, status: e.target.value } : item))}>
                    {statusOptions.map(status => (<option key={status} value={status}>{status.replace("_", " ")}</option>))}
                  </select>
                </label>
                <button className="btn primary" type="button" onClick={handleStatusUpdate}>Save status</button>
              </div>
              <div className="dispatchBlock">
                <label>
                  Estimated arrival
                  <input
                    type="datetime-local"
                    value={selectedEnquiry.estimated_arrival ? String(selectedEnquiry.estimated_arrival).slice(0, 16) : ""}
                    onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, estimated_arrival: e.target.value } : item))}
                  />
                </label>
                <label>
                  Truck registration
                  <input value={selectedEnquiry.truck_registration || ""} onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, truck_registration: e.target.value } : item))} placeholder="KDA 123A" />
                </label>
                <label>
                  Driver name
                  <input value={selectedEnquiry.driver_name || ""} onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, driver_name: e.target.value } : item))} placeholder="Driver name" />
                </label>
                <label>
                  Driver phone
                  <input value={selectedEnquiry.driver_phone || ""} onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, driver_phone: e.target.value } : item))} placeholder="+254..." />
                </label>
                <label className="fullWidthDispatch">
                  Current checkpoint / location
                  <input value={selectedEnquiry.current_checkpoint || ""} onChange={e => setEnquiries(prev => prev.map(item => item.id === selectedEnquiry.id ? { ...item, current_checkpoint: e.target.value } : item))} placeholder="e.g. Sagana weighbridge" />
                </label>
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
