# Web Frontend

Patient and doctor interfaces of the appointment booking application.

## Tech Stack

- React 19 + TypeScript
- Vite
- oxlint and Prettier

## Scope

- Patient interface: sign in, view available slots, book and cancel appointments
- Doctor interface: daily calendar, appointment list, mark attended / no-show

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
