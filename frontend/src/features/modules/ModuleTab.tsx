import { useSettings, useUpdateSettings } from '../../hooks/useSystemConfig';
import type { AppSettings, SecurityLevel } from '../../api/types';

const LEVEL_INFO: Record<SecurityLevel, { title: string; desc: string }> = {
  LOW: {
    title: '낮음',
    desc: '블랙리스트와 트리거 상황은 부분 마스킹, 일반 욕설은 사용자 검토로 표시합니다. 오탐을 최소화합니다.',
  },
  MEDIUM: {
    title: '보통 (권장)',
    desc: '블랙리스트는 완전 차단하고, 트리거 상황은 부분 마스킹, 일반 욕설은 사용자 검토로 표시합니다.',
  },
  HIGH: {
    title: '강함',
    desc: '블랙리스트와 트리거 상황을 모두 완전 차단하고, 일반 욕설도 부분 마스킹합니다. 강력하게 보호합니다.',
  },
};

const LEVELS: SecurityLevel[] = ['LOW', 'MEDIUM', 'HIGH'];

const ModuleTab = () => {
  const { data: settings } = useSettings();
  const updateSettingsMutation = useUpdateSettings();

  if (!settings) return null;

  const handleLevelChange = (level: SecurityLevel) => {
    updateSettingsMutation.mutate({ ...settings, intensity: level });
  };

  const toggleAiSoften = () => {
    updateSettingsMutation.mutate({ ...settings, aiSoftenEnabled: !settings.aiSoftenEnabled });
  };

  const toggleModule = (key: keyof typeof settings.modules) => {
    updateSettingsMutation.mutate({
      ...settings,
      modules: { ...settings.modules, [key]: !settings.modules[key] }
    });
  };

  const currentInfo = LEVEL_INFO[settings.intensity] ?? LEVEL_INFO.MEDIUM;

  const moduleList = [
    { key: 'criticism', label: '악성 비난/협박', desc: '특정 대상에 대한 맹목적 비난, 협박, 저주 등을 탐지합니다.' },
    { key: 'sexual', label: '성희롱/음란물', desc: '성적 수치심을 유발하거나 음란한 묘사가 포함된 댓글을 탐지합니다.' },
    { key: 'pii', label: '개인정보 유출', desc: '전화번호, 주소, 실명, 계좌번호 등 개인정보가 포함된 댓글을 탐지합니다.' },
    { key: 'politics', label: '정치/혐오 발언', desc: '영상 맥락과 무관한 정치적 선동이나 혐오 발언을 필터링합니다.' },
    { key: 'spam', label: '스팸/도배/광고', desc: '광고성 링크, 도배, 무의미한 문자열 반복 등을 탐지합니다.' },
    { key: 'family', label: '가족 비하/패륜 표현', desc: '부모, 자녀 등 가족을 대상으로 한 모욕적이거나 패륜적인 발언을 탐지합니다.' },
    { key: 'basic', label: '기본 유해/필터 회피', desc: '일반 유해 표현, 변형 표현, 필터 회피 시도를 탐지합니다.' },
  ] as const;

  return (
    <div className="p-4 space-y-8">
      {/* 보안 모드 설정 */}
      <section>
        <h3 className="text-sm font-bold mb-4">보안 모드</h3>
        <div className="grid grid-cols-3 gap-2">
          {LEVELS.map((level) => (
            <button
              key={level}
              onClick={() => handleLevelChange(level)}
              className={`py-2 text-sm font-bold rounded-lg border transition-all ${
                settings.intensity === level
                  ? 'bg-indigo-500 text-white border-indigo-500 shadow-sm'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'
              }`}
            >
              {LEVEL_INFO[level].title}
            </button>
          ))}
        </div>

        <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
          <div className="flex items-center mb-2">
            <span className="font-bold text-sm text-indigo-600 mr-2">
              {currentInfo.title}
            </span>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{currentInfo.desc}</p>
        </div>
      </section>

      {/* AI 순화 마스킹 설정 */}
      <section className="pt-4 border-t border-gray-100">
        <div className="flex items-start justify-between">
          <div className="pr-4">
            <div className="font-bold text-sm">AI 순화 마스킹</div>
            <div className="text-xs text-gray-500 mt-1 leading-relaxed">
              부분 마스킹 시 '***' 대신 AI가 문맥에 맞게 순화한 텍스트로 바꿔 표시합니다.
            </div>
          </div>
          <button
            onClick={toggleAiSoften}
            className={`w-12 h-6 rounded-full relative transition-colors shrink-0 ${settings.aiSoftenEnabled ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-all shadow-sm ${settings.aiSoftenEnabled ? 'left-6.5 translate-x-1' : 'left-0.5'}`} />
          </button>
        </div>
      </section>

      {/* 모듈 설정 */}
      <section className="space-y-6 pt-4 border-t border-gray-100">
        <h3 className="text-sm font-bold mb-2">모듈 설정</h3>
        {moduleList.map((item) => {
          const moduleKey = item.key as keyof AppSettings['modules'];
          const isActive = settings.modules[moduleKey] ?? false;

          return (
            <div key={item.key} className="flex items-start justify-between">
              <div className="pr-4">
                <div className="font-bold text-sm">{item.label}</div>
                <div className="text-xs text-gray-500 mt-1 leading-relaxed">{item.desc}</div>
              </div>
              <button
                onClick={() => toggleModule(item.key)}
                className={`w-12 h-6 rounded-full relative transition-colors shrink-0 ${isActive ? 'bg-green-500' : 'bg-gray-300'}`}
              >
                <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-all shadow-sm ${isActive ? 'left-6.5 translate-x-1' : 'left-0.5'}`} />
              </button>
            </div>
          );
        })}
      </section>
    </div>
  );
};

export default ModuleTab;
