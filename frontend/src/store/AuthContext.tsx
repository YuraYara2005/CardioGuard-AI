import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import type { AuthUser, UserRole } from '../types';

// ── Mock credential store ─────────────────────────────────────────────────────
const MOCK_USERS: Record<string, AuthUser & { password: string }> = {
  'doctor@cardioguard.ai': {
    id: 'usr-001',
    name: 'Dr. Sarah Al-Rashidi',
    email: 'doctor@cardioguard.ai',
    role: 'Doctor',
    password: 'doctor123',
    avatarUrl: undefined,
  },

  'patient@cardioguard.ai': {
    id: 'usr-002',
    name: 'أحمد حسن',
    email: 'patient@cardioguard.ai',
    role: 'Patient',
    password: 'patient123',
    avatarUrl: undefined,

    // Links this login to Ahmed Hassan in Patient Registry
    patientId: 'P001',
  },
};

// ── Context shape ─────────────────────────────────────────────────────────────
interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  switchRole: (role: UserRole) => void; // dev helper
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    // Persist session across page refreshes
    const stored = localStorage.getItem('cg_user');
    return stored ? (JSON.parse(stored) as AuthUser) : null;
  });

  const login = useCallback(async (email: string, password: string) => {
    const record = MOCK_USERS[email.toLowerCase()];
    if (!record || record.password !== password) {
      throw new Error('Invalid credentials. Please try again.');
    }
    const { password: _pw, ...authUser } = record;
    setUser(authUser);
    localStorage.setItem('cg_user', JSON.stringify(authUser));
    // In production: swap for real JWT from apiClient.post('/auth/login')
    localStorage.setItem('cg_auth_token', 'mock-jwt-token');
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('cg_user');
    localStorage.removeItem('cg_auth_token');
  }, []);

  // Convenience method for dev / demo mode to flip roles instantly
  const switchRole = useCallback(
    (role: UserRole) => {
      if (!user) return;
      const updated: AuthUser = { ...user, role };
      setUser(updated);
      localStorage.setItem('cg_user', JSON.stringify(updated));
    },
    [user],
  );

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, login, logout, switchRole }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}
