import { useCallback, useState } from 'react';

const ONBOARDING_SEEN_STORAGE_KEY = 'brainit_onboarding_seen';

const readIsFirstVisit = () => {
  if (typeof window === 'undefined') {
    return false;
  }

  try {
    return window.localStorage.getItem(ONBOARDING_SEEN_STORAGE_KEY) === null;
  } catch {
    return true;
  }
};

const useOnboardingFirstVisit = () => {
  const [isFirstVisit, setIsFirstVisit] = useState(readIsFirstVisit);

  const markOnboardingCompleted = useCallback(() => {
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(ONBOARDING_SEEN_STORAGE_KEY, 'true');
      } catch {
        // Ignore storage errors and still update in-memory state.
      }
    }
    setIsFirstVisit(false);
  }, []);

  return { isFirstVisit, markOnboardingCompleted };
};

export default useOnboardingFirstVisit;
export { ONBOARDING_SEEN_STORAGE_KEY, readIsFirstVisit };
