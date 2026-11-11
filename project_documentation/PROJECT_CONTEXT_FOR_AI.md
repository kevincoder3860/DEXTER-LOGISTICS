# Project Context for Another AI Assistant

## What the project does
This repository is a React + Vite website for Dextere Haulers Limited. It presents the company as a Kenyan and East African transport and logistics business offering passenger transport, cargo haulage, and cross-border logistics services. The current implementation is a branded landing page with simple enquiry and tracking UI flows.

## Architecture
The project architecture is intentionally simple:
- Frontend: React + Vite
- Styling: CSS file with responsive rules
- Runtime state: browser React state only
- Backend: none
- Database: none
- API layer: none

The app renders as a single-page experience from `src/App.jsx` and is styled by `src/styles.css`.

## Technology stack
- React 18
- Vite 6
- Lucide React icons
- CSS custom styling
- Google Fonts
- Unsplash image background
- Node.js/npm for development and build

## Main features
- Company landing page and hero section
- Service section for passenger, cargo, cross-border, and parcel logistics
- Coverage section for Kenya/East Africa branding
- Shipment tracking form placeholder
- Booking enquiry form placeholder
- Contact details section
- Responsive navigation and mobile menu

## Database structure
No database is implemented. There are no models or migrations. This project does not yet have persistent storage.

## Important API endpoints
None exist. The forms do not call any API. Local UI handlers only change message state.

## Current development status
Verified status:
- Build succeeds (`npm run build`)
- Static frontend renders and works as a page
- UI is functional as a marketing demo

Not yet implemented or verified:
- Real booking submission
- Real shipment tracking
- Data persistence
- Backend API
- Authentication and authorization
- Payment flow
- Fleet and route operational data

## Existing problems
- No backend or database
- No real business logic or persistence
- Demo-only booking and tracking flows
- No security model or access control
- README explicitly identifies missing functionality

## Technical constraints
- This is a frontend-only repo with no server-side logic.
- It should not be treated as a production logistics platform.
- Any feature that modifies or stores data will require a backend and database architecture.
- The project is currently best described as a preliminary marketing website and prototype inquiry flow.

## What should be done next
1. Clarify whether this is a marketing landing page or a full logistics platform.
2. Create a backend and database for bookings, shipments, customers, and admin users.
3. Replace placeholder enquiry handlers with real submission flows.
4. Add validation, security, and environment configuration.
5. Verify all business data and operational claims before production.

## What must not be changed without permission
- Do not treat the current forms as real functional systems.
- Do not assume live tracking, payment processing, or data storage already works.
- Do not add operational logic to the frontend without creating the required backend architecture.
- Do not assume business claims or route coverage are verified without source-of-truth business data.

## Bottom line
This project is currently a static company website prototype, not a live logistics management system. It has a successful build and clean UI, but the operational backend required for real bookings, tracking, and business processing does not exist yet.
