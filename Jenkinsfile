pipeline {
    agent any

    environment {
        SONAR_TOKEN = credentials('sonar-token')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                    apt-get update
                    apt-get install -y python3 python3-pip python3-venv nodejs npm
                '''
            }
        }

        stage('Backend - Install') {
            steps {
                dir('backend') {
                    sh '''
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
                    withCredentials([string(credentialsId: 'DJANGO_SECRET_KEY', variable: 'DJANGO_SECRET_KEY')]) {
                        sh '''
                            . .venv/bin/activate
                            python3 -m pytest --cov=. --cov-report=xml:coverage.xml
                        '''
                    }
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

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'

                    withSonarQubeEnv('SonarQube') {
                        withEnv(["SCANNER_HOME=${scannerHome}"]) {
                            sh(
                                script: '''
                                    $SCANNER_HOME/bin/sonar-scanner \
                                    -Dsonar.projectKey=fashionstore \
                                    -Dsonar.projectName=FashionStore \
                                    -Dsonar.sources=. \
                                    -Dsonar.python.version=3.13 \
                                    -Dsonar.sourceEncoding=UTF-8 \
                                    -Dsonar.python.coverage.reportPaths=backend/coverage.xml \
                                    -Dsonar.token=$SONAR_TOKEN
                                ''',
                                label: 'Run SonarScanner'
                            )
                        }
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
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