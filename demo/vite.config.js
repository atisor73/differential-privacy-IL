import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

const isPagesBuild = process.env.GITHUB_ACTIONS === 'true';
const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1] ?? 'differential-privacy';
const configuredBase = process.env.VITE_BASE_PATH;

export default defineConfig({
  base: configuredBase ?? (isPagesBuild ? `/${repoName}/` : '/'),
  plugins: [
    svelte({
      compilerOptions: {
        compatibility: {
          componentApi: 4
        }
      }
    })
  ],
  server: {
    port: 5173,
    host: '0.0.0.0'
  }
});
