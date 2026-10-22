# Web Frontend

Patient and department interfaces of the appointment booking application.

## Tech Stack

- React 19 + TypeScript
- Vite
- oxlint and Prettier
- Vitest and Testing Library

## Scope

The screens follow the approved final design, [`docs/design/appointment-system.html`](../../docs/design/appointment-system.html) (#66): a white base, blue for the patient and department screens and red for alerts.

- Entry page with "Hasta Girişi" and "Departman Girişi"; the management panel is not part of the website, it stays in the admin service
- Patient portal: a weekly calendar of the department's slots, the booking summary and confirmation, "Randevularım" with cancellation and the patient's sent SMS messages
- Department panel: today's program in "Bekleyen", "Geldi" and "Gelmedi" columns with attendance marking, a week strip, the next patient, the days of the dataset read-only with their recorded outcome, and the working hours with slot opening

The system has one department and no doctor; no screen names a doctor. Patients are the patients of the public dataset and are shown as `Hasta <PatientId>`. Patients see a time only as "Müsait" or "Dolu", and neither patients nor the department see risks, thresholds or overbooking decisions.

## Pages

The interface is in Turkish. After login every screen has a ribbon with the signed-in account and "Çıkış", a menu rail on the left, the main area and a side panel on the right; on narrow screens the side panel moves under the main area and the menu above it, so nothing is hidden. Each screen has its own address (React Router) and browser tab title; signed-out visitors of a patient or department screen are sent to the login form of its role and continue to that screen after signing in.

| Address                            | Screen                                                                                                                                                    | Who        |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `/`                                | Entry page: "Hasta Girişi" and "Departman Girişi"                                                                                                         | Signed out |
| `/giris/hasta`, `/giris/departman` | Patient login (patient number) and department login (username)                                                                                            | Signed out |
| `/randevu-al`                      | Randevu al: weekly calendar (Monday–Friday, eight weeks ahead) with "Müsait", "Dolu", "Randevum" and "Kapalı"; summary and confirmation in the side panel | Patient    |
| `/randevularim`                    | Randevularım: upcoming appointments with cancellation, SMS messages                                                                                       | Patient    |
| `/departman`                       | Bugünkü program: the board of a day, the week strip, the dataset days, the next patient                                                                   | Department |
| `/calisma-takvimi`                 | Çalışma takvimi: working hours and opening slots                                                                                                          | Department |

Addresses of the earlier site lead to their new screen (`/online-randevu`, `/hasta-listesi`, `/giris/hekim`); any other address leads to the entry page.

On the department board, today's appointments move between the columns with "Geldi", "Gelmedi" and "Geri al"; attendance is marked only for today. Other days are read-only: future days list their bookings, past days show the recorded outcome, and the days of the dataset (29 April – 8 June 2016, chosen in "Veri seti günleri") show all their real appointments with the outcome of the dataset and the no-show rate; long days are shown in parts.

The hospital is fictional. Its name is defined only in `src/config.ts` (`INSTITUTION_NAME`), next to the department's name (`DEPARTMENT_NAME`). The theme is in `src/index.css`.

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
| `npm test`             | Run the tests once           |

## Tests

Component tests use Vitest and Testing Library in jsdom (`vitest.config.ts`). They render the whole app at a page address and replace `fetch` with a fake backend (`src/test/backend.tsx`), so no backend has to run. They cover the entry page and the routing, patient login with the patient number and department login with the username (including the messages for wrong credentials and too many attempts), the weekly calendar with only free, full, own and closed times, booking and its refusal, browsing the weeks, "Randevularım" with cancellation and the SMS messages, and the department board: today's columns with attendance marking and taking a mark back, another day read-only, and a dataset day read-only and in parts.

```bash
npm test
# or keep them running while you edit
npx vitest
```
