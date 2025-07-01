// Basic Fastify server setup

const fastify = require('fastify')({ logger: true })

fastify.get('/', async (request, reply) => {
  return { message: 'Welcome to the API Gateway' }
})

const start = async () => {
  try {
    await fastify.listen({ port: 8000, host: '0.0.0.0' })
    fastify.log.info(`server listening on ${fastify.server.address().port}`)
  } catch (err) {
    fastify.log.error(err)
    process.exit(1)
  }
}

start()
