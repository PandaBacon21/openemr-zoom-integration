import React, { createContext, useContext, useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { getFeatures, type Features } from "../api/config";

const DEFAULT_FEATURES: Features = { db_browser: false, epic_zcc: false };

interface FeaturesContextType {
  features: Features;
  loading: boolean;
}

const FeaturesContext = createContext<FeaturesContextType>({
  features: DEFAULT_FEATURES,
  loading: true,
});

export const FeaturesProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { isAuthenticated } = useAuth();
  const [features, setFeatures] = useState<Features>(DEFAULT_FEATURES);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!isAuthenticated) {
      setFeatures(DEFAULT_FEATURES);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    getFeatures()
      .then((res) => {
        if (!cancelled) setFeatures(res.data);
      })
      .catch(() => {
        if (!cancelled) setFeatures(DEFAULT_FEATURES);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  return (
    <FeaturesContext.Provider value={{ features, loading }}>
      {children}
    </FeaturesContext.Provider>
  );
};

export const useFeatures = () => useContext(FeaturesContext);
