import { create } from "zustand"

export interface Song {
  title: string
  url: string
  webpage_url: string
  thumbnail: string
  duration: number
  uploader: string
}

interface MusicState {
  current: Song | null
  queue: Song[]
  paused: boolean
  loop: boolean
  loop_queue: boolean
  volume: number
  elapsed: number
  guildId: string | null
  guildName: string
  guildIcon: string

  setCurrent: (song: Song | null) => void
  setQueue: (queue: Song[]) => void
  setPaused: (v: boolean) => void
  setLoop: (v: boolean) => void
  setLoopQueue: (v: boolean) => void
  setVolume: (v: number) => void
  setElapsed: (v: number) => void
  setGuild: (id: string, name: string, icon: string) => void
}

export const useMusicStore = create<MusicState>((set) => ({
  current: null,
  queue: [],
  paused: false,
  loop: false,
  loop_queue: false,
  volume: 80,
  elapsed: 0,
  guildId: null,
  guildName: "",
  guildIcon: "",

  setCurrent: (song) => set({ current: song }),
  setQueue: (queue) => set({ queue }),
  setPaused: (paused) => set({ paused }),
  setLoop: (loop) => set({ loop }),
  setLoopQueue: (loop_queue) => set({ loop_queue }),
  setVolume: (volume) => set({ volume }),
  setElapsed: (elapsed) => set({ elapsed }),
  setGuild: (guildId, guildName, guildIcon) => set({ guildId, guildName, guildIcon }),
}))
