# Web Frontend

Patient and department interfaces of the appointment booking application.

## Tech Stack

- React 19 + TypeScript
- Vite
- oxlint and Prettier
- Vitest and Testing Library

## Scope

- Website of the fictional "Şehir Hastanesi": home page, hospital, the department "Aile Hekimliği" with its working hours, announcements, patient guide, contact and directions
- Patient interface: sign in with the dataset patient number, view available slots, book and cancel appointments
- Department interface: patient list with date, week overview and upcoming appointments, attendance marking, working hours

The system has one department and no doctor; no screen names a doctor. Patients are the patients of the public dataset and are shown as `Hasta <PatientId>`.

## Pages

The interface is in Turkish. Every page sits in the hospital site frame: a header with the logo, the hospital name, the main menu, "Online Randevu" and the login links (the account menu and "Çıkış" once signed in), and a footer with fictional contact details and the course project disclaimer. Each screen has its own address (React Router) and browser tab title; signed-out visitors of a patient or department screen are sent to the login form of its role and continue to that screen after signing in. "Online Randevu" in the header, on the home page and on the department page leads to the booking; the signed-in department is told that booking needs a patient account.

| Address                            | Screen                                                                  | Who        |
| ---------------------------------- | ----------------------------------------------------------------------- | ---------- |
| `/`                                | Home page: quick actions, latest announcements, about the hospital      | Everyone   |
| `/hastanemiz`                      | About the hospital                                                      | Everyone   |
| `/aile-hekimligi`                  | The department: description, weekly working hours, Online Randevu       | Everyone   |
| `/duyurular`, `/duyurular/:id`     | Announcements and an announcement                                       | Everyone   |
| `/hasta-rehberi`                   | Patient guide                                                           | Everyone   |
| `/iletisim-ve-ulasim`              | Contact and directions                                                  | Everyone   |
| `/giris/hasta`, `/giris/departman` | Patient login (patient number) and department login (username)          | Signed out |
| `/online-randevu`                  | Online Randevu: day → time (`/randevu-al` redirects here)               | Patient    |
| `/randevularim`                    | Active and past appointments, cancellation                              | Patient    |
| `/hasta-listesi`                   | Patient list of a day, week overview, upcoming appointments, attendance | Department |
| `/calisma-takvimi`                 | Working hours and opening slots                                         | Department |

The hospital is fictional. Its name is defined only in `src/config.ts` (`INSTITUTION_NAME`), next to the department's name (`DEPARTMENT_NAME`); the logo is a simple SVG made for the project (`src/site/Logo.tsx`). The department's working hours come from the web backend's public list (`GET /public/doctors`, no sign-in), whose one record is the department. The static content (announcements, guide, contact details) is data in `src/content/site.ts`; addresses, phone numbers and e-mail addresses are made up and use the `sehirhastanesi.example` domain.

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

Component tests use Vitest and Testing Library in jsdom (`vitest.config.ts`). They render the whole app at a page address and replace `fetch` with a fake backend (`src/test/backend.tsx`), so no backend has to run. They cover patient login with the patient number and department login with the username (including the messages for wrong credentials), booking with day → time, the extra appointment display of a partly booked slot, cancellation, the department's daily list with attendance marking, the week overview and the upcoming appointments, the too-many-attempts message, the hospital site frame and static pages without any doctor, the department page, and Online Randevu through the login.

```bash
npm test
# or keep them running while you edit
npx vitest
```
