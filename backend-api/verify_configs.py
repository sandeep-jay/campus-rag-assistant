"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

from app.core.config_manager import settings


def main() -> None:
    """Print out key settings to verify configuration manager is working correctly."""
    
    print('Verifying configuration settings...')
    print(f'PROJECT_NAME: {settings.PROJECT_NAME}')
    print(f'VERSION: {settings.VERSION}')
    print(f'ENVIRONMENT: {settings.ENVIRONMENT}')
    print(f'APP_ENV: {settings.APP_ENV}')
    print(f'DATABASE_URL: {settings.DATABASE_URL}')
    print(f'AWS_REGION: {settings.AWS_REGION}')
    print(f'BEDROCK_MODEL_ID: {settings.BEDROCK_MODEL_ID}')
    print(f'BEDROCK_KNOWLEDGE_BASE_ID: {settings.BEDROCK_KNOWLEDGE_BASE_ID}')
    print(f'LANGCHAIN_PROJECT: {settings.LANGCHAIN_PROJECT}')
    print(f'LOGGING_LEVEL: {settings.LOGGING_LEVEL}')
    print(f'LOG_TO_FILE: {settings.LOG_TO_FILE}')
    print(f'LOGGING_LOCATION: {settings.LOGGING_LOCATION}')
    print('Configuration verification complete.')


if __name__ == '__main__':
    main()
