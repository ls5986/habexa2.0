import { useState, useEffect } from 'react';
import api from '../services/api';

export const useSettings = () => {
  const [profile, setProfile] = useState(null);
  const [alertSettings, setAlertSettings] = useState(null);
  const [costSettings, setCostSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProfile = async () => {
    try {
      const response = await api.get('/settings/profile');
      setProfile(response.data);
    } catch (err) {
      setError(err.message);
    }
  };

  const fetchAlertSettings = async () => {
    try {
      const response = await api.get('/settings/alerts');
      setAlertSettings(response.data);
    } catch (err) {
      setError(err.message);
    }
  };

  const fetchCostSettings = async () => {
    try {
      const response = await api.get('/settings/costs');
      setCostSettings(response.data);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([fetchProfile(), fetchAlertSettings(), fetchCostSettings()]);
      setLoading(false);
    };
    loadAll();
  }, []);

  const updateProfile = async (data) => {
    try {
      const response = await api.put('/settings/profile', data);
      setProfile(response.data);
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to update profile');
    }
  };

  const updateAlertSettings = async (data) => {
    try {
      const response = await api.put('/settings/alerts', data);
      setAlertSettings(response.data);
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to update alert settings');
    }
  };

  const updateCostSettings = async (data) => {
    try {
      const response = await api.put('/settings/costs', data);
      setCostSettings(response.data);
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to update cost settings');
    }
  };

  return {
    profile,
    alertSettings,
    costSettings,
    loading,
    error,
    refetch: async () => {
      await Promise.all([fetchProfile(), fetchAlertSettings(), fetchCostSettings()]);
    },
    updateProfile,
    updateAlertSettings,
    updateCostSettings,
  };
};

