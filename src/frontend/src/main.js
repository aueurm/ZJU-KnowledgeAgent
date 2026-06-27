import { createApp } from 'vue'
import App from './App.vue'
import 'virtual:uno.css'

const app = createApp(App)

app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue Error]', info, err)
}

app.mount('#app')