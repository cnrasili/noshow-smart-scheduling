# Web Frontend

Patient and doctor interfaces of the appointment booking application.

## Tech Stack

- React 19 + TypeScript
- Vite
- oxlint and Prettier

## Scope

- Patient interface: sign in, view available slots, book and cancel appointments
- Doctor interface: daily calendar, appointment list, mark attended / no-show

## Pages

The interface is in Turkish. Each screen has its own address (React Router); signed-out visitors are sent to the login form of the page's role, and signed-in users to their own home page.

| Address                        | Screen                                            | Who        |
| ------------------------------ | ------------------------------------------------- | ---------- |
| `/`                            | Landing page                                      | Everyone   |
| `/giris/hasta`, `/giris/hekim` | Patient and doctor login                          | Signed out |
| `/randevu-al`                  | Book an appointment: branch → doctor → day → time | Patient    |
| `/randevularim`                | Active and past appointments, cancellation        | Patient    |
| `/hasta-listesi`               | Daily patient list and attendance                 | Doctor     |
| `/calisma-takvimi`             | Working hours and opening slots                   | Doctor     |

The institution name shown in the interface is a fictional placeholder in `src/config.ts`.

## Development

```bash
npm install
npm run dev
```

The app runs on http://localhost:5173 and calls the web backend at `VITE_API_URL` (default `http://localhost:8000`).

| Command                | Purpose                      |
| ---------------------- | ---------------------------- |
| `npm run dev`          | Start the development server |
| `npm run build`        | Type-check and build         |
| `npm run lint`         | Lint with oxlint             |
| `npm run format`       | Format with Prettier         |
| `npm run format:check` | Check formatting             |
