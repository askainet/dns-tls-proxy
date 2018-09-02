#!/usr/bin/env groovy

podTemplate(label: 'mypod', containers: [
    containerTemplate(name: 'python', image: 'python:3.6-alpine', command: 'cat', ttyEnabled: true),
    containerTemplate(name: 'docker', image: 'docker', command: 'cat', ttyEnabled: true),
    containerTemplate(name: 'kubectl', image: 'lachlanevenson/k8s-kubectl:v1.11.2', command: 'cat', ttyEnabled: true),
  ],
  volumes: [
    hostPathVolume(mountPath: '/var/run/docker.sock', hostPath: '/var/run/docker.sock'),
  ],
  serviceAccount: 'jenkins'
  ) {

    node('mypod') {

        def myRepo = checkout scm
        def gitCommit = myRepo.GIT_COMMIT
        def gitBranch = myRepo.GIT_BRANCH
        def shortGitCommit = "${gitCommit[0..6]}"
        def dockerNamespace = "askainet"
        def dockerImage = "dns-tls-proxy"

        // stage('Python test') {
        //     container('python') {
        //         sh """
        //             # apk update && apk add build-base python-dev py-gevent
        //             # pip install -r requirements.txt
        //             # pytest -v
        //             echo '${shortGitCommit}'
        //         """
        //     }
        // }

        stage('Docker image') {
            container('docker') {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_HUB_USER', passwordVariable: 'DOCKER_HUB_PASSWORD')]) {
                    sh 'docker login -u "${DOCKER_HUB_USER}" -p "${DOCKER_HUB_PASSWORD}"'
                    sh """
                        # docker pull ${dockerNamespace}/${dockerImage} || true
                        docker build -t ${dockerNamespace}/${dockerImage}:${shortGitCommit} .
                        docker push ${dockerNamespace}/${dockerImage}:${shortGitCommit}
                    """
                }
            }
        }

        stage('Run kubectl') {
          container('kubectl') {
            sh """
                kubectl get ns ${gitBranch} || kubectl create ns ${gitBranch}
                sed -i 's#${dockerNamespace}/${dockerImage}:latest#${dockerNamespace}/${dockerImage}:${shortGitCommit}#' k8s/deployment.yaml
                kubectl --namespace=${gitBranch} apply -f k8s/service.yaml
                kubectl --namespace=${gitBranch} apply -f k8s/deployment.yaml
            """
          }
        }

    }

}
