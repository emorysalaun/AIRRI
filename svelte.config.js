import adapter from '@sveltejs/adapter-static';

const repoName = 'AIRRI'; // <-- change this

export default {
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: '404.html'
    }),
    paths: {
      base: process.env.NODE_ENV === 'production' ? `/${repoName}` : ''
    }
  }
};
