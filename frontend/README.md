# OracleX frontend

The OracleX frontend is a React and TypeScript single-page application. It uses the same-origin `/api` path so a company deployment does not need a browser-visible backend hostname.

Development commands:

```powershell
npm ci
npm run lint
npm run build
```

The release process compiles `dist` on a connected build machine, then copies only those static files into the pinned nginx runtime image. The disconnected production host does not run Node.js or `npm install`.
