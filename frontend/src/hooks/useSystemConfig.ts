import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchSystemConfig, updateSystemConfig, addDictionaryWord, fetchDictionary, deleteDictionaryWord, linkYoutubeChannel, unlinkYoutubeChannel } from '../api/services';
import type { AppSettings, SystemConfigResponse, DictionaryRequest } from '../api/types';

const MODULE_MAP: Record<keyof AppSettings['modules'], string> = {
  modified: 'MODIFIED',
  sexual: 'SEXUAL',
  privacy: 'PRIVACY',
  aggression: 'AGGRESSION',
  political: 'POLITICAL',
  spam: 'SPAM',
  family: 'FAMILY',
};

// [변환기] 백엔드 -> 프론트엔드
const transformToAppSettings = (data: SystemConfigResponse): AppSettings => {
  const modules: AppSettings['modules'] = {
    modified: false,
    sexual: false,
    privacy: false,
    aggression: false,
    political: false,
    spam: false,
    family: false,
  };

  const enabledModulesArray = data.enabled_modules ? data.enabled_modules.split(',').map(m => m.trim()) : [];

  (Object.keys(MODULE_MAP) as Array<keyof typeof MODULE_MAP>).forEach((uiKey) => {
    const backendKey = MODULE_MAP[uiKey];
    if (enabledModulesArray.includes(backendKey)) {
      modules[uiKey] = true;
    }
  });

  return {
    intensity: data.security_level,
    aiSoftenEnabled: data.ai_soften_enabled,
    modules,
  };
};

// [변환기] 프론트엔드 -> 백엔드
const transformToBackendUpdate = (settings: AppSettings) => {
  const enabled_modules_array: string[] = [];

  (Object.keys(settings.modules) as Array<keyof typeof settings.modules>).forEach((uiKey) => {
    if (settings.modules[uiKey]) {
      enabled_modules_array.push(MODULE_MAP[uiKey]);
    }
  });

  return {
    security_level: settings.intensity,
    ai_soften_enabled: settings.aiSoftenEnabled,
    enabled_modules: enabled_modules_array.join(','),
  };
};

// SystemConfigResponse placeholder — initialData 가 아니라 placeholderData 로 사용해야
// TanStack 이 데이터를 "seeded & fresh" 로 간주하지 않고 즉시 fetchSystemConfig 를 실행한다.
// 기존엔 initialData + staleTime:Infinity 조합 탓에 로그인 직후 유튜브 채널이
// null 로 고정되어 있다가 focus 등 외부 트리거로만 갱신되는 지연 버그가 있었다.
const PLACEHOLDER_CONFIG: SystemConfigResponse = {
  user_id: 0,
  security_level: 'MEDIUM',
  enabled_modules: 'ALL',
  ai_soften_enabled: false,
  use_detail_ai_model: false,
  youtube_channel_id: null,
  youtube_channel_name: null,
  youtube_channel_url: null,
  youtube_thumbnail_url: null,
};

// 1. 설정 조회 Hook (Config API)
export const useSettings = () => {
  return useQuery({
    queryKey: ['system-config'],
    queryFn: () => fetchSystemConfig(),
    select: transformToAppSettings,
    placeholderData: PLACEHOLDER_CONFIG,
    staleTime: 1000 * 60 * 5,
  });
};

// YouTube 채널 정보 조회 (settings에서 추출)
export const useYoutubeChannel = () => {
  return useQuery({
    queryKey: ['system-config'],
    queryFn: () => fetchSystemConfig(),
    placeholderData: PLACEHOLDER_CONFIG,
    staleTime: 1000 * 60 * 5,
    select: (data: SystemConfigResponse) => ({
      channel_id: data.youtube_channel_id,
      channel_name: data.youtube_channel_name,
      channel_url: data.youtube_channel_url,
      thumbnail_url: data.youtube_thumbnail_url,
    }),
  });
};

// YouTube 채널 연동
export const useLinkYoutubeChannel = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (channelId: string) => linkYoutubeChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] });
    },
  });
};

// YouTube 채널 연동 해제
export const useUnlinkYoutubeChannel = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => unlinkYoutubeChannel(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] });
    },
  });
};

// 2. 설정 업데이트 Hook (Config API)
export const useUpdateSettings = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (newSettings: AppSettings) => {
      const payload = transformToBackendUpdate(newSettings);
      return updateSystemConfig(payload);
    },

    onMutate: async (newSettings) => {
      await queryClient.cancelQueries({ queryKey: ['system-config'] });
      queryClient.setQueryData(['system-config'], newSettings);
    },

    onError: (err) => {
      console.error("설정 저장 실패 (화면 유지):", err);
    },

    // 보안 모드/모듈 변경은 클라이언트 derivePolicy로 즉시 반영된다.
    // 따라서 full-analysis / keyword-analysis 캐시를 무효화할 필요가 없다 (= 재분석 금지).

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] });
    },
  });
};

// 1. 조회 Hook
export const useDictionary = () => {
  return useQuery({
    queryKey: ['system-dictionary'],
    queryFn: async () => {
      const result = await fetchDictionary();
      return {
        whitelist: result.whitelist || [],
        blacklist: result.blacklist || [],
      };
    },
    staleTime: 1000 * 60 * 5,
  });
};

// 2. 추가 Hook (POST) - [서버 죽어도 화면엔 추가됨]
export const useAddDictionaryWord = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (req: DictionaryRequest) => 
      addDictionaryWord(req.list_type, req.words),
    
    // 낙관적 업데이트 (추가)
    onMutate: async (newWordReq) => {
      await queryClient.cancelQueries({ queryKey: ['system-dictionary'] });
      
      queryClient.setQueryData(['system-dictionary'], (old: any) => {
        const current = old || { whitelist: [], blacklist: [] };
        const isWhite = newWordReq.list_type === 'whitelist';
        
        return {
          ...current,
          whitelist: isWhite ? [...current.whitelist, ...newWordReq.words] : current.whitelist,
          blacklist: !isWhite ? [...current.blacklist, ...newWordReq.words] : current.blacklist,
        };
      });
    },
    onSuccess: async () => {
      if (typeof chrome !== 'undefined' && chrome.storage?.session) {
        await chrome.storage.session.remove('guard-filter-analysis');
      }
      // refetchType: 'all' → 어떤 탭이든 비활성 쿼리도 refetch (FilterTab에서도 재분석 트리거)
      queryClient.invalidateQueries({ queryKey: ['full-analysis'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['keyword-analysis'], refetchType: 'all' });
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['system-dictionary'] }),
  });
};

// 3. 삭제 Hook (DELETE) - [서버 죽어도 화면엔 반영됨]
export const useDeleteDictionaryWord = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (req: DictionaryRequest) => 
      deleteDictionaryWord(req.list_type, req.words),
    
    // 낙관적 업데이트 (삭제)
    onMutate: async (delWordReq) => {
      await queryClient.cancelQueries({ queryKey: ['system-dictionary'] });

      queryClient.setQueryData(['system-dictionary'], (old: any) => {
        const current = old || { whitelist: [], blacklist: [] };
        const isWhite = delWordReq.list_type === 'whitelist';
        const targetWords = delWordReq.words; // 삭제할 단어들

        return {
          ...current,
          // filter를 사용해 삭제할 단어들을 제외시킴
          whitelist: isWhite 
            ? current.whitelist.filter((w: string) => !targetWords.includes(w)) 
            : current.whitelist,
          blacklist: !isWhite
            ? current.blacklist.filter((w: string) => !targetWords.includes(w))
            : current.blacklist,
        };
      });
    },
    onSuccess: async () => {
      if (typeof chrome !== 'undefined' && chrome.storage?.session) {
        await chrome.storage.session.remove('guard-filter-analysis');
      }
      queryClient.invalidateQueries({ queryKey: ['full-analysis'], refetchType: 'all' });
      queryClient.invalidateQueries({ queryKey: ['keyword-analysis'], refetchType: 'all' });
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['system-dictionary'] }),
  });
};