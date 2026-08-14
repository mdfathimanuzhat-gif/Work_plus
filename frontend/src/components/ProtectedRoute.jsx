/**
 * Route guard placeholder.
 *
 * Real JWT session checks will be added in the authentication phase.
 * Until then, children render so layout and routing can be developed.
 */
export default function ProtectedRoute({ children }) {
  return children;
}
