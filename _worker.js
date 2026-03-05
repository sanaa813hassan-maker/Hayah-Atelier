import { handleRequest } from './mysite/flask_app';

export default {
  async fetch(request, env, ctx) {
    return await handleRequest(request);
  },
};
