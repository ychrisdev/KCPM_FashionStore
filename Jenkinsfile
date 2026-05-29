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
                    sh '''
                        apt-get update -y
                        apt-get install -y python3 python3-pip python3-venv
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install -r requirements.txt
                    '''
                }
            }
        }

        stage('Backend - Test') {
            steps {
                dir('backend') {
                    sh '''
                        . .venv/bin/activate
                        python3 manage.py test
                    '''
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