# ⚙️ Estándares Técnicos — {{NOMBRE_DEL_PROYECTO}}

## Stack Tecnológico

### Frontend
- Framework: [ej: React 18 + TypeScript]
- UI Library: [ej: Tailwind CSS + Headless UI]
- State Management: [ej: Zustand]
- Routing: [ej: React Router v6]

### Backend
- Lenguaje: [ej: Node.js 18]
- Framework: [ej: Express.js]
- Base de Datos: [ej: PostgreSQL + Prisma ORM]
- Cache: [ej: Redis]

### Herramientas
- Build: [ej: Vite]
- Testing: [ej: Jest (unit), Playwright (E2E)]
- Linting: [ej: ESLint + Prettier]
- CI/CD: [ej: GitHub Actions]
- Contenedores: [ej: Docker + Docker Compose]

## Decisiones Técnicas Clave
- **Autenticación**: JWT con refresh tokens.
- **Manejo de Errores**: Código de error estandarizado + logging estructurado.
- **Internacionalización**: i18next con archivos JSON por idioma.
- **Performance**: Lazy loading en rutas, compresión Brotli.

## Restricciones y Políticas
- **Seguridad**: Todo password hasheado con bcrypt, CORS estricto, sanitización de inputs.
- **Rendimiento**: Máximo 2s de carga en mobile 3G.
- **Compatibilidad**: Soporte para Chrome, Firefox, Safari (últimas 2 versiones).
- **Dependencias**: Solo librerías auditadas y con > 10k downloads/semana en npm.

## Servicios Externos
- **Pagos**: Stripe
- **Email**: SendGrid
- **Mapas**: Google Maps API
- **Analytics**: Mixpanel
