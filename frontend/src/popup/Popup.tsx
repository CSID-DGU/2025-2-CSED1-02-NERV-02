import { useState, useEffect } from 'react';
import Header from '../components/layout/Header';
import TabNavigation from '../components/layout/TabNavigation';
import ChatTab from '../features/chat/ChatTab';
import ModuleTab from '../features/modules/ModuleTab';
import FilterTab from '../features/filter/FilterTab';
import AnalysisTab from '../features/analysis/AnalysisTab';
import { login, register } from '../api/services';

type TabType = 'CHAT' | 'MODULE' | 'FILTER' | 'ANALYSIS';
type View = 'login' | 'register' | 'app';

// --- 로그인 뷰 ---
const LoginView = ({ onLogin, onGoRegister }: { onLogin: () => void; onGoRegister: () => void }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(username, password);
      await chrome.storage.local.set({ access_token: data.access_token, user_id: String(data.user_id) });
      onLogin();
    } catch (err: any) {
      setError(err.response?.data?.detail || '로그인 실패');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-[800px] h-[600px] flex flex-col bg-white">
      <Header />
      <main className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="w-full max-w-sm bg-white border border-gray-100 rounded-xl p-8 shadow-sm">
          <h2 className="text-xl font-bold text-gray-900 mb-6">로그인</h2>
          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">아이디</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-black transition-colors"
                placeholder="아이디를 입력하세요"
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">비밀번호</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-black transition-colors"
                placeholder="비밀번호를 입력하세요"
                required
              />
            </div>
            {error && <p className="text-sm text-red-500 text-center">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="mt-2 py-2.5 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </form>
          <div className="mt-4 text-center text-sm text-gray-500">
            계정이 없으신가요?{' '}
            <button onClick={onGoRegister} className="text-black font-medium hover:underline">
              회원가입
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

// --- 회원가입 뷰 ---
const RegisterView = ({ onRegister, onGoLogin }: { onRegister: () => void; onGoLogin: () => void }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) { setError('비밀번호가 일치하지 않습니다'); return; }
    if (password.length < 6) { setError('비밀번호는 최소 6자 이상이어야 합니다'); return; }
    setLoading(true);
    try {
      const data = await register(username, password);
      await chrome.storage.local.set({ access_token: data.access_token, user_id: String(data.user_id) });
      onRegister();
    } catch (err: any) {
      setError(err.response?.data?.detail || '회원가입 실패');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-[800px] h-[600px] flex flex-col bg-white">
      <Header />
      <main className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="w-full max-w-sm bg-white border border-gray-100 rounded-xl p-8 shadow-sm">
          <h2 className="text-xl font-bold text-gray-900 mb-6">회원가입</h2>
          <form onSubmit={handleRegister} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">아이디 (최소 3자)</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-black transition-colors"
                placeholder="아이디를 입력하세요"
                minLength={3}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">비밀번호 (최소 6자)</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-black transition-colors"
                placeholder="비밀번호를 입력하세요"
                minLength={6}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-gray-700">비밀번호 확인</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="px-3 py-2.5 border border-gray-200 rounded-lg text-sm outline-none focus:border-black transition-colors"
                placeholder="비밀번호를 다시 입력하세요"
                minLength={6}
                required
              />
            </div>
            {error && <p className="text-sm text-red-500 text-center">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="mt-2 py-2.5 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              {loading ? '가입 중...' : '회원가입'}
            </button>
          </form>
          <div className="mt-4 text-center text-sm text-gray-500">
            이미 계정이 있으신가요?{' '}
            <button onClick={onGoLogin} className="text-black font-medium hover:underline">
              로그인
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

// --- 메인 앱 뷰 ---
const AppView = ({ onLogout }: { onLogout: () => void }) => {
  const [activeTab, setActiveTab] = useState<TabType>('CHAT');

  return (
    <div className="w-[800px] h-[600px] flex flex-col bg-white">
      <Header onLogout={onLogout} />
      <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="flex-1 overflow-y-auto p-4 bg-gray-50">
        {activeTab === 'CHAT' && <ChatTab />}
        {activeTab === 'MODULE' && <ModuleTab />}
        {activeTab === 'FILTER' && <FilterTab />}
        {activeTab === 'ANALYSIS' && <AnalysisTab />}
      </main>
    </div>
  );
};

// --- 루트 컴포넌트 ---
const Popup = () => {
  const [view, setView] = useState<View>('login');

  useEffect(() => {
    chrome.storage.local.get('access_token').then(({ access_token }) => {
      if (access_token) setView('app');
    });
  }, []);

  const handleLogout = async () => {
    await chrome.storage.local.remove(['access_token', 'user_id']);
    setView('login');
  };

  if (view === 'login') return <LoginView onLogin={() => setView('app')} onGoRegister={() => setView('register')} />;
  if (view === 'register') return <RegisterView onRegister={() => setView('app')} onGoLogin={() => setView('login')} />;
  return <AppView onLogout={handleLogout} />;
};

export default Popup;
