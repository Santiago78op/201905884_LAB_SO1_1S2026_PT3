# Comandos para la Calificación del Proyecto

El namespace es un recurso lógico en Kubernetes que permite organizar y aislar recursos dentro de un clúster.

## Criterio 1.1: Implementación de Gateway API.

| Comando | Descripción |
|---------|-------------|
| `kubectl get gateway -n military-pipeline` | Un recurso de tipo Gateway con una IP externa asignada. |
| `kubectl get httproute -n military-pipeline` | Rutas configuradas para /grpc-#carnet  |
| `kubectl describe httproute rust-api-route -n military-pipeline` | Describe la ruta HTTP para la API Rust. |

## Criterios 1.2 y 1.3: API Rust y Servicios Go.

| Comando | Descripción |
|---------|-------------|
| `kubectl get hpa -n military-pipeline` | El HPA de la API Rust con targets de CPU > 30%. |
| `kubectl get deployments -n military-pipeline` | Son los despliegues de la aplicación en el namespace `military-pipeline`. |
| `kubectl logs deployment/rust-api -n military-pipeline` | Logs mostrando la recepción de JSON desde Locust. |
| `kubectl logs deployment/go-server -n military-pipeline` | Logs indicando que se recibió un mensaje vía gRPC desde el cliente Go. |

## Criterio 1.4: Despliegue de Zot en una VM externa y uso de HTTPS.

| Comando | Descripción |
|---------|-------------|
| `gcloud compute ssh santiagojulian78op@zot-registry --zone=us-central1-a` | Conecta a la máquina virtual en Google Cloud. |
| `docker ps o systemctl status zot` | Un contenedor o servicio de Zot corriendo en el puerto 443/5000. |
| `curl http://34.68.174.65:5000/v2/_catalog` | Obtiene el catálogo de repositorios en Zot. |

## Criterio 1.5: Broker y Consumidor.

| Comando | Descripción |
|---------|-------------|
| `kubectl get pods -n military-pipeline ` | Pods del broker y consumidor corriendo en el namespace `military-pipeline`. |
| `kubectl get pods -n messaging` | Pods del broker y consumidor corriendo en el namespace `messaging`. |
| `kubectl exec -it -n messaging rabbitmq-5bbd7c6bb8-c8f6z -- rabbitmqctl list_queues` | Lista las colas en RabbitMQ para verificar que el consumidor está recibiendo mensajes. |
| `kubectl logs deployment/rabbitmq -n messaging` | Logs del servicio de RabbitMQ en el namespace `messaging`. |

## Criterios 1.6 y 1.7: Punto crítico para verificar Valkey y Grafana en kubervirt
| Comando | Descripción |
|---------|-------------|
| `kubectl get vms -n messaging` | Verifica que las máquinas virtuales de Valkey y Grafana estén corriendo en el namespace `messaging`. |
| `kubectl get vmi -n messaging` | Verifica que las máquinas virtuales de Valkey y Grafana estén corriendo en el namespace `messaging`. |
| `kubectl describe vmi grafana-vm -n messaging` | Describe la máquina virtual de Grafana para verificar su configuración. |
| `kubectl describe vmi valkey-vm -n messaging` | Describe la máquina virtual de Valkey para verificar su configuración. |

## Comando a realizar 

```bash
kubectl run mi-nginx --image=nginx:latest
```