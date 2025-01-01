'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';

const UserContext = createContext({
  user: null,
  team: null,
  teams: [],
  chats: [],
  projects: [],
  createAccount: async () => {},
  addChat: async () => {},
  refreshChats: async () => {},
  refreshProjects: async () => {},
  refreshTeams: async () => {},
  refreshUser: async () => {},
});

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  const [chats, setChats] = useState([]);
  const [teams, setTeams] = useState([]);
  const [team, setTeam] = useState(null);
  const [projects, setProjects] = useState([]);

  const fetchUserData = async () => {
    const [chats, teams] = await Promise.all([api.getChats(), api.getTeams()]);

    setChats(chats);
    setTeams(teams);

    if (!localStorage.getItem('team') && teams.length > 0) {
      setTeam(teams[0]);
      localStorage.setItem('team', teams[0].id);
    } else {
      setTeam(teams.find((t) => t.id + '' === localStorage.getItem('team')));
    }
  };

  useEffect(() => {
    if (localStorage.getItem('token')) {
      api
        .getCurrentUser()
        .then(setUser)
        .catch((e) => {
          if (e.message.includes('token')) {
            localStorage.removeItem('token');
            localStorage.removeItem('team');
            setUser(null);
            setTeam(null);
            setChats([]);
            setTeams([]);
            setProjects([]);
            window.location.href = '/';
          }
        });
      fetchUserData();
    }
  }, []);

  useEffect(() => {
    if (team?.id) {
      api.getTeamProjects(team.id).then(setProjects);
    }
  }, [team?.id]);

  const createAccount = async (username) => {
    const user = await api.createAccount(username);
    setUser(user);
    await fetchUserData();
    return user;
  };

  const addChat = (chat) => {
    setChats((prev) => [...prev, chat]);
  };

  const refreshChats = async () => {
    const chats = await api.getChats();
    setChats(chats);
  };

  const refreshProjects = async () => {
    const projects = await api.getTeamProjects(team.id);
    setProjects(projects);
  };

  const refreshTeams = async () => {
    const teams = await api.getTeams();
    setTeams(teams);
    setTeam(teams.find((t) => t.id + '' === localStorage.getItem('team')));
  };

  const refreshUser = async () => {
    const user = await api.getCurrentUser();
    setUser(user);
  };

  return (
    <UserContext.Provider
      value={{
        user,
        chats,
        teams,
        team,
        projects,
        createAccount,
        addChat,
        refreshUser,
        refreshChats,
        refreshProjects,
        refreshTeams,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export const useUser = () => useContext(UserContext);
