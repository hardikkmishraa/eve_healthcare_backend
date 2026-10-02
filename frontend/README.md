# EVE Healthcare - Patient Web Portal

A clean, responsive, student-built production frontend for the EVE Healthcare diagnostic booking system. Built with React, Vite, TypeScript, and Tailwind CSS, interfacing directly with the FastAPI REST API.

---

## Features

- **Authentication**: JWT-based patient signup, login, persistent sessions, and profile view.
- **Diagnostic Centres**: Browse verified diagnostic centres with city and name search.
- **Test Offerings**: Browse diagnostic tests with category filters and authoritative centre pricing.
- **Appointment Booking**: Schedule appointments with slot validation (preventing bookings within 1 hour).
- **Booking Management**: View booking history, status badges (`PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`), and cancellation support.
- **Payment Simulation**: Integration with the simulated payment API to test success and failure scenarios.

---

## Tech Stack

- **Framework**: React 19 + Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Routing**: React Router v7
- **HTTP Client**: Axios with JWT request/response interceptors
- **Icons**: Lucide React

---

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- EVE Healthcare FastAPI backend running locally (default: `http://localhost:8000`)

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

### Backend Configuration

The frontend connects to the backend through an environment variable.

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and verify or set `VITE_API_BASE_URL`:
   ```bash
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

   All API calls route through `src/services/api.ts` which uses this base URL.

### Running in Development

Start the local Vite development server:
```bash
npm run dev
```

The application will be accessible at: `http://localhost:5173`

### Building for Production

Compile TypeScript and build the production bundle:
```bash
npm run build
```

Preview the production build locally:
```bash
npm run preview
```

---

## Project Structure

```
frontend/
├── public/
├── src/
│   ├── components/       # Reusable UI components (Navbar, Footer, StatusBadge, etc.)
│   ├── context/          # React Context (AuthContext for JWT session state)
│   ├── hooks/            # Custom React hooks (useAuth)
│   ├── pages/            # Page components (Home, Centres, Tests, BookTest, Bookings, Payment, Profile)
│   ├── services/         # Axios API clients (auth, centres, bookings, payments)
│   ├── types/            # TypeScript interfaces matching FastAPI Pydantic schemas
│   ├── utils/            # Formatting helpers (currency, datetime, appointment validation)
│   ├── App.tsx           # Route definitions and layouts
│   ├── main.tsx          # Application entrypoint
│   └── index.css         # Tailwind base styles and theme tokens
├── .env.example          # Environment variable template
├── package.json
└── vite.config.ts
```
