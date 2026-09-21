This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Sign-in, Google key and demo replay

Set these in `web/.env.local` to turn on Google sign-in (Firebase Auth). Leave them unset for local mode: no sign-in,
no bearer token, no key prompts.

```
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

With Firebase on, every non-demo API call carries `Authorization: Bearer <ID token>` (`src/lib/api.ts`), and the run
event stream is read with `fetch` (`EventSource` cannot send headers). Signed-out visitors see a landing page with
**View demo run**, which uses the public `/demo/runs` routes (run ids start with `demo-`) and is labelled a recorded example.

Endpoints the UI expects from the API: `GET/PUT/DELETE /me/key` (`PUT` body `{"google_key": "..."}`),
`POST /me/key/test` (body `{"google_key": "..."}` or empty to use the stored key), `POST /demo/runs`, and
`/demo/runs/{id}/status|events|decision|result`. A `401` whose body contains `missing_google_key` opens the key panel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
