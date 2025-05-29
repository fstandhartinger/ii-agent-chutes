import { useState, useCallback } from 'react';
import { TAB, ActionStep } from '@/typings/agent';

export interface UIState {
  activeTab: TAB;
  currentActionData: ActionStep | undefined;
  activeFileCodeEditor: string;
  browserUrl: string;
  isMobileMenuOpen: boolean;
  isMobileDetailPaneOpen: boolean;
  deployedUrl: string;
  logoClickCount: number;
  showNativeToolToggle: boolean;
  showConsentDialog: boolean;
  shouldShakeConnectionIndicator: boolean;
  showReloadButton: boolean;
}

export interface UIStateActions {
  setActiveTab: React.Dispatch<React.SetStateAction<TAB>>;
  setCurrentActionData: React.Dispatch<React.SetStateAction<ActionStep | undefined>>;
  setActiveFileCodeEditor: React.Dispatch<React.SetStateAction<string>>;
  setBrowserUrl: React.Dispatch<React.SetStateAction<string>>;
  setIsMobileMenuOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setIsMobileDetailPaneOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setDeployedUrl: React.Dispatch<React.SetStateAction<string>>;
  setLogoClickCount: React.Dispatch<React.SetStateAction<number>>;
  incrementLogoClickCount: () => void;
  setShowNativeToolToggle: React.Dispatch<React.SetStateAction<boolean>>;
  setShowConsentDialog: React.Dispatch<React.SetStateAction<boolean>>;
  setShouldShakeConnectionIndicator: React.Dispatch<React.SetStateAction<boolean>>;
  triggerShakeConnectionIndicator: () => void;
  setShowReloadButton: React.Dispatch<React.SetStateAction<boolean>>;
  resetUIState: () => void;
}

export type UseUIStateReturn = UIState & UIStateActions;

const initialUIState: UIState = {
  activeTab: TAB.BROWSER,
  currentActionData: undefined,
  activeFileCodeEditor: "",
  browserUrl: "",
  isMobileMenuOpen: false,
  isMobileDetailPaneOpen: false,
  deployedUrl: "",
  logoClickCount: 0,
  showNativeToolToggle: false,
  showConsentDialog: false,
  shouldShakeConnectionIndicator: false,
  showReloadButton: false,
};

export const useUIState = (initialState?: Partial<UIState>): UseUIStateReturn => {
  const [activeTab, setActiveTab] = useState<TAB>(initialState?.activeTab || initialUIState.activeTab);
  const [currentActionData, setCurrentActionData] = useState<ActionStep | undefined>(initialState?.currentActionData || initialUIState.currentActionData);
  const [activeFileCodeEditor, setActiveFileCodeEditor] = useState<string>(initialState?.activeFileCodeEditor || initialUIState.activeFileCodeEditor);
  const [browserUrl, setBrowserUrl] = useState<string>(initialState?.browserUrl || initialUIState.browserUrl);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(initialState?.isMobileMenuOpen || initialUIState.isMobileMenuOpen);
  const [isMobileDetailPaneOpen, setIsMobileDetailPaneOpen] = useState<boolean>(initialState?.isMobileDetailPaneOpen || initialUIState.isMobileDetailPaneOpen);
  const [deployedUrl, setDeployedUrl] = useState<string>(initialState?.deployedUrl || initialUIState.deployedUrl);
  const [logoClickCount, setLogoClickCount] = useState<number>(initialState?.logoClickCount || initialUIState.logoClickCount);
  const [showNativeToolToggle, setShowNativeToolToggle] = useState<boolean>(initialState?.showNativeToolToggle || initialUIState.showNativeToolToggle);
  const [showConsentDialog, setShowConsentDialog] = useState<boolean>(initialState?.showConsentDialog || initialUIState.showConsentDialog);
  const [shouldShakeConnectionIndicator, setShouldShakeConnectionIndicator] = useState<boolean>(initialState?.shouldShakeConnectionIndicator || initialUIState.shouldShakeConnectionIndicator);
  const [showReloadButton, setShowReloadButton] = useState<boolean>(initialState?.showReloadButton || initialUIState.showReloadButton);

  const incrementLogoClickCount = useCallback(() => {
    setLogoClickCount(prev => prev + 1);
  }, []);

  const triggerShakeConnectionIndicator = useCallback(() => {
    setShouldShakeConnectionIndicator(true);
    setTimeout(() => setShouldShakeConnectionIndicator(false), 1000);
  }, []);

  const resetUIState = useCallback(() => {
    setActiveTab(initialUIState.activeTab);
    setCurrentActionData(initialUIState.currentActionData);
    setActiveFileCodeEditor(initialUIState.activeFileCodeEditor);
    // browserUrl might be preserved or reset based on specific needs
    setIsMobileMenuOpen(initialUIState.isMobileMenuOpen);
    // isMobileDetailPaneOpen might also be preserved or reset
    setDeployedUrl(initialUIState.deployedUrl);
    // logoClickCount and showNativeToolToggle are usually persistent user interactions, so not reset here
    setShowConsentDialog(initialUIState.showConsentDialog);
    setShouldShakeConnectionIndicator(initialUIState.shouldShakeConnectionIndicator);
    setShowReloadButton(initialUIState.showReloadButton);
  }, []);

  return {
    activeTab,
    currentActionData,
    activeFileCodeEditor,
    browserUrl,
    isMobileMenuOpen,
    isMobileDetailPaneOpen,
    deployedUrl,
    logoClickCount,
    showNativeToolToggle,
    showConsentDialog,
    shouldShakeConnectionIndicator,
    showReloadButton,
    setActiveTab,
    setCurrentActionData,
    setActiveFileCodeEditor,
    setBrowserUrl,
    setIsMobileMenuOpen,
    setIsMobileDetailPaneOpen,
    setDeployedUrl,
    setLogoClickCount,
    incrementLogoClickCount,
    setShowNativeToolToggle,
    setShowConsentDialog,
    setShouldShakeConnectionIndicator,
    triggerShakeConnectionIndicator,
    setShowReloadButton,
    resetUIState,
  };
};
