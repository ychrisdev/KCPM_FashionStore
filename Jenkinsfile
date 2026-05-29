pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Backend - Install') {
            steps {
                dir('backend') {
                    sh 'pip3 install -r requirements.txt --break-system-packages'
                }
            }
        }

        stage('Backend - Test') {
            steps {
                dir('backend') {
                    sh 'python3 manage.py test'
                }
            }
        }

        stage('Frontend - Install') {
            steps {
                dir('frontend') {
                    sh 'npm install'
                }
            }
        }

        stage('Frontend - Build') {
            steps {
                dir('frontend') {
                    sh 'npm run build'
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline chạy thành công!'
        }
        failure {
            echo 'Pipeline thất bại! Kiểm tra log.'
        }
    }
}