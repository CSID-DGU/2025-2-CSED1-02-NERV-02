interface HeaderProps {
  onLogout?: () => void;
}

const Header = ({ onLogout }: HeaderProps) => {
  return (
    <header className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-100 shrink-0">
      <div className="flex items-center">
        {/* 로고 아이콘 (SVG) */}
        <div className="flex items-center justify-center w-8 h-8 mr-3 bg-black rounded-full">
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="white" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            className="w-5 h-5"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>
        <h1 className="text-xl font-bold text-gray-900 font-sans">GuardFilter</h1>
      </div>

      {onLogout && (
        <button
          onClick={onLogout}
          className="text-sm text-gray-400 hover:text-gray-700 transition-colors"
        >
          로그아웃
        </button>
      )}
    </header>
  );
};

export default Header;