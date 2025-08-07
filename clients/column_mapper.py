"""
컬럼 매핑 유틸리티
한국어 컬럼명을 영문으로 자동 변환
"""
import re
from typing import Dict, List
from deep_translator import GoogleTranslator


class ColumnMapper:
    """한국어 컬럼명을 영문으로 매핑하는 클래스"""
    
    def __init__(self):
        # 핵심 필드는 직접 매핑 (정확성 보장)
        self.direct_mapping = {
            '고객명': 'customer_name',
            '연락처': 'phone',
            '전화번호': 'phone',
            '휴대폰': 'phone',
            '핸드폰': 'phone',
            '주소': 'address',
            '이메일': 'email',
            'E-mail': 'email',
            'Email': 'email',
            '생년월일': 'birth_date',
            '성별': 'gender',
            '직업': 'occupation',
            '회사': 'company',
            '직장': 'company',
            
            # 갤러리 특화 필드들
            '구매 작가명': 'purchased_artist',
            '관심 작가': 'interested_artist',
            '선호 작가': 'preferred_artist',
            '작품 캡션 정보': 'artwork_caption',
            '(원) 작품가': 'original_price',
            '원작품가': 'original_price',
            '작품가': 'artwork_price',
            '(실재) 입금가': 'actual_payment',
            '실제입금가': 'actual_payment',
            '입금가': 'payment_amount',
            '결제 방식': 'payment_method',
            '결제방법': 'payment_method',
            '특이사항': 'notes',
            '메모': 'notes',
            '비고': 'notes',
            '등록일': 'registration_date',
            '가입일': 'registration_date',
            '판매 루트': 'sales_route',
            '판매루트': 'sales_route',
            '날짜': 'date'
        }
        
        # 번역기 초기화
        self.translator = GoogleTranslator(source='ko', target='en')
    
    def normalize_korean_columns(self, headers: List[str]) -> Dict[str, str]:
        """
        한국어 컬럼명 리스트를 영문으로 정규화
        
        Args:
            headers: 한국어 컬럼명 리스트
            
        Returns:
            Dict[한국어, 영문]: 매핑 딕셔너리
        """
        result = {}
        need_translation = []
        
        # 디버깅용 로그
        print(f"🔍 입력된 헤더: {headers}")
        
        # 1. 직접 매핑 처리
        for header in headers:
            clean_header = header.strip()
            
            # 빈 헤더나 자동 생성된 컬럼명 처리
            if not clean_header or clean_header.startswith('column'):
                print(f"⚠️ 빈 헤더 또는 자동 생성된 컬럼명 발견: '{header}'")
                result[header] = f"unknown_field_{len(result) + 1}"
                continue
                
            if clean_header in self.direct_mapping:
                result[clean_header] = self.direct_mapping[clean_header]
                print(f"✅ 직접 매핑: {clean_header} → {self.direct_mapping[clean_header]}")
            else:
                need_translation.append(clean_header)
        
        # 2. 번역이 필요한 컬럼들 처리
        for header in need_translation:
            try:
                translated = self._translate_and_normalize(header)
                result[header] = translated
                print(f"🌐 번역 매핑: {header} → {translated}")
            except Exception as e:
                print(f"❌ 번역 실패 ({header}): {e}")
                # 번역 실패시 fallback (문자 정리만)
                fallback = self._fallback_normalize(header)
                result[header] = fallback
                print(f"🔄 Fallback 매핑: {header} → {fallback}")
        
        print(f"📋 최종 매핑 결과: {result}")
        return result
    
    def _translate_and_normalize(self, korean_text: str) -> str:
        """
        한국어 텍스트를 번역하여 snake_case로 변환
        """
        # 번역 수행
        translated = self.translator.translate(korean_text)
        
        # snake_case로 정규화
        return self._to_snake_case(translated)
    
    def _to_snake_case(self, text: str) -> str:
        """
        영문 텍스트를 snake_case로 변환
        """
        # 특수문자 제거 및 소문자 변환
        cleaned = re.sub(r'[^\w\s]', '', text.lower())
        
        # 공백을 언더스코어로 변환
        snake_case = re.sub(r'\s+', '_', cleaned)
        
        # 연속된 언더스코어 정리
        snake_case = re.sub(r'_+', '_', snake_case)
        
        # 앞뒤 언더스코어 제거
        return snake_case.strip('_') or 'unknown_field'
    
    def _fallback_normalize(self, korean_text: str) -> str:
        """
        번역 실패시 fallback 처리
        한국어를 단순 정리하여 사용 가능한 형태로 만듦
        """
        # 괄호, 특수문자 제거
        cleaned = re.sub(r'[^\w가-힣\s]', '', korean_text)
        
        # 공백을 언더스코어로
        normalized = re.sub(r'\s+', '_', cleaned.lower())
        
        # 한글은 romanize 하지 않고 그대로 유지 (최신 시스템들은 대부분 지원)
        return normalized or 'unknown_field'
    
    def map_excel_data(self, excel_data: List[Dict], column_mapping: Dict[str, str]) -> List[Dict]:
        """
        엑셀 데이터를 매핑된 컬럼명으로 변환
        
        Args:
            excel_data: 원본 엑셀 데이터
            column_mapping: 컬럼 매핑 정보
            
        Returns:
            변환된 데이터
        """
        mapped_data = []
        
        for row in excel_data:
            mapped_row = {}
            
            for korean_key, value in row.items():
                english_key = column_mapping.get(korean_key, korean_key)
                mapped_row[english_key] = value
            
            mapped_data.append(mapped_row)
        
        return mapped_data


# 편의 함수들
def normalize_columns(headers: List[str]) -> Dict[str, str]:
    """컬럼 정규화 편의 함수"""
    mapper = ColumnMapper()
    return mapper.normalize_korean_columns(headers)


def map_excel_data(excel_data: List[Dict]) -> tuple[List[Dict], Dict[str, str]]:
    """
    엑셀 데이터 전체 처리 편의 함수
    
    Returns:
        (변환된_데이터, 컬럼_매핑_정보)
    """
    if not excel_data:
        return [], {}
    
    mapper = ColumnMapper()
    
    # 헤더 추출
    headers = list(excel_data[0].keys())
    
    # 컬럼 매핑 생성
    column_mapping = mapper.normalize_korean_columns(headers)
    
    # 데이터 변환
    mapped_data = mapper.map_excel_data(excel_data, column_mapping)
    
    return mapped_data, column_mapping


# 테스트 함수
def test_column_mapper():
    """컬럼 매퍼 테스트"""
    mapper = ColumnMapper()
    
    test_headers = [
        '고객명', '연락처', '주소', '구매이력', 
        '관심장르', '(원) 작품가', '특이사항'
    ]
    
    result = mapper.normalize_korean_columns(test_headers)
    
    print("=== 컬럼 매핑 테스트 결과 ===")
    for korean, english in result.items():
        print(f"{korean} → {english}")
    
    return result


if __name__ == "__main__":
    test_column_mapper()