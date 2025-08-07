"""
AI 기반 스키마 자동 생성 모듈
"""
import json
import re
from typing import Dict, List, Any, Optional
from django.conf import settings


class AISchemaGenerator:
    """AI API를 사용하여 데이터에서 자동으로 스키마를 생성"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'GEMINI_API_KEY', None)
    
    def analyze_excel_data(self, excel_data: List[Dict]) -> Dict[str, Any]:
        """
        엑셀 데이터를 분석하여 최적의 스키마 생성
        
        Args:
            excel_data: 엑셀에서 파싱된 원본 데이터
            
        Returns:
            {
                'fields': [
                    {
                        'name': 'customer_name',
                        'type': 'text',
                        'required': True,
                        'korean_name': '고객명'
                    }, ...
                ],
                'mapping': {
                    '고객명': 'customer_name',
                    '연락처': 'phone_number'
                }
            }
        """
        if not excel_data:
            return {'fields': [], 'mapping': {}}
        
        # 샘플 데이터 준비 (처음 3개 행)
        sample_data = excel_data[:3]
        headers = list(sample_data[0].keys()) if sample_data else []
        
        # AI 프롬프트 생성
        prompt = self._create_analysis_prompt(headers, sample_data)
        
        # AI API 호출 (여기서는 구조만 제시)
        schema_response = self._call_ai_api(prompt)
        
        # AI 응답 파싱
        return self._parse_ai_response(schema_response)
    
    def _create_analysis_prompt(self, headers: List[str], sample_data: List[Dict]) -> str:
        """AI 분석용 프롬프트 생성"""
        return f"""
다음은 고객 관리 시스템에 업로드된 엑셀 데이터입니다.
이 데이터를 분석하여 최적의 데이터베이스 스키마를 생성해주세요.

헤더: {headers}
샘플 데이터:
{json.dumps(sample_data, ensure_ascii=False, indent=2)}

다음 JSON 형식으로 응답해주세요:
{{
    "fields": [
        {{
            "korean_name": "원본 한글 필드명",
            "english_name": "영문_snake_case_필드명",
            "type": "text|number|date|boolean|email|phone",
            "required": true|false,
            "description": "필드 설명"
        }}
    ]
}}

규칙:
1. 영문 필드명은 snake_case 사용
2. 고객명, 이름 -> customer_name
3. 연락처, 전화번호 -> phone_number  
4. 이메일 -> email
5. 주소 -> address
6. 날짜 형식 데이터는 type을 'date'로
7. 숫자 데이터는 'number'로
8. 필수 필드: 고객명, 연락처
"""
    
    def _call_ai_api(self, prompt: str) -> str:
        """
        AI API 호출 (Gemini, GPT 등)
        실제 구현시에는 선택한 AI 서비스의 API를 사용
        """
        # 예시: Gemini API 호출
        # import google.generativeai as genai
        # genai.configure(api_key=self.api_key)
        # model = genai.GenerativeModel('gemini-pro')
        # response = model.generate_content(prompt)
        # return response.text
        
        # 임시 더미 응답 (실제 구현시 제거)
        return '''
{
    "fields": [
        {
            "korean_name": "고객명",
            "english_name": "customer_name", 
            "type": "text",
            "required": true,
            "description": "고객의 이름"
        },
        {
            "korean_name": "연락처",
            "english_name": "phone_number",
            "type": "phone", 
            "required": true,
            "description": "고객 연락처"
        },
        {
            "korean_name": "주소",
            "english_name": "address",
            "type": "text",
            "required": false,
            "description": "고객 주소"
        }
    ]
}
        '''
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """AI 응답을 파싱하여 스키마 정보 추출"""
        try:
            # JSON 추출 (AI 응답에서 JSON 부분만)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # 매핑 정보 생성
            mapping = {}
            fields = []
            
            for field in data.get('fields', []):
                korean_name = field['korean_name']
                english_name = field['english_name']
                
                mapping[korean_name] = english_name
                fields.append({
                    'name': english_name,
                    'type': field['type'],
                    'required': field['required'],
                    'korean_name': korean_name,
                    'description': field.get('description', '')
                })
            
            return {
                'fields': fields,
                'mapping': mapping
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"AI 응답 파싱 오류: {e}")
            return {'fields': [], 'mapping': {}}
    
    def create_dynamic_model_fields(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI 생성 스키마를 바탕으로 동적 모델 필드 생성
        JSONField 구조로 변환
        """
        json_structure = {}
        
        for field in schema['fields']:
            field_name = field['name']
            field_type = field['type']
            
            # 기본값 설정
            if field_type == 'text':
                json_structure[field_name] = ""
            elif field_type == 'number':
                json_structure[field_name] = 0
            elif field_type == 'date':
                json_structure[field_name] = None
            elif field_type == 'boolean':
                json_structure[field_name] = False
            else:
                json_structure[field_name] = ""
        
        return json_structure


# 사용 예시
def process_excel_with_ai(excel_data: List[Dict]) -> Dict[str, Any]:
    """
    엑셀 데이터를 AI로 분석하여 처리
    """
    generator = AISchemaGenerator()
    
    # 1. AI가 스키마 생성
    schema = generator.analyze_excel_data(excel_data)
    
    # 2. 데이터 매핑
    processed_data = []
    for row in excel_data:
        mapped_row = {}
        
        # AI가 생성한 매핑 정보로 변환
        for korean_key, english_key in schema['mapping'].items():
            if korean_key in row:
                mapped_row[english_key] = row[korean_key]
        
        processed_data.append(mapped_row)
    
    return {
        'schema': schema,
        'data': processed_data
    }