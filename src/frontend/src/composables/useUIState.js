import { ref } from 'vue'

const activeTab = ref('merge')

export function useUIState() {
  return {
    activeTab
  }
}