from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User, Gallery
from artworks.models import Artwork
from clients.models import Client


class Command(BaseCommand):
    help = '기존 작품 및 고객 데이터를 test2 갤러리에 할당하는 마이그레이션'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 변경 없이 변경될 데이터만 표시',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='이미 갤러리가 할당된 데이터도 test2로 변경',
        )

    def handle(self, *args, **options):
        try:
            # test2 사용자와 갤러리 확인
            test2_user = User.objects.get(username='test2')
            test2_gallery = test2_user.gallery
            
            if not test2_gallery:
                self.stdout.write(
                    self.style.ERROR('test2 사용자에게 갤러리가 할당되지 않았습니다.')
                )
                return
                
            self.stdout.write(f'target 갤러리: {test2_gallery.name} (ID: {test2_gallery.id})')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('test2 사용자를 찾을 수 없습니다.')
            )
            return

        # 현재 상태 출력
        self.stdout.write('\n=== 현재 데이터 상태 ===')
        
        if options['force']:
            artworks_to_migrate = Artwork.objects.all()
            clients_to_migrate = Client.objects.all()
            self.stdout.write('모든 데이터를 test2 갤러리로 이동합니다.')
        else:
            artworks_to_migrate = Artwork.objects.filter(gallery__isnull=True)
            clients_to_migrate = Client.objects.filter(gallery__isnull=True)
            self.stdout.write('갤러리가 할당되지 않은 데이터만 test2 갤러리로 이동합니다.')
        
        self.stdout.write(f'이동할 작품 수: {artworks_to_migrate.count()}개')
        self.stdout.write(f'이동할 고객 수: {clients_to_migrate.count()}개')

        # 이동할 데이터 상세 정보
        if artworks_to_migrate.exists():
            self.stdout.write('\n=== 이동할 작품 목록 ===')
            for artwork in artworks_to_migrate[:10]:  # 처음 10개만 표시
                current_gallery = artwork.gallery.name if artwork.gallery else '없음'
                self.stdout.write(f'- 작품 ID {artwork.id}: "{artwork.title_ko}" (현재 갤러리: {current_gallery})')
            if artworks_to_migrate.count() > 10:
                self.stdout.write(f'... 외 {artworks_to_migrate.count() - 10}개')

        if clients_to_migrate.exists():
            self.stdout.write('\n=== 이동할 고객 목록 ===')
            for client in clients_to_migrate[:10]:  # 처음 10개만 표시
                current_gallery = client.gallery.name if client.gallery else '없음'
                self.stdout.write(f'- 고객 ID {client.id}: "{client.name}" (현재 갤러리: {current_gallery})')
            if clients_to_migrate.count() > 10:
                self.stdout.write(f'... 외 {clients_to_migrate.count() - 10}개')

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('\n--dry-run 모드: 실제 변경은 수행되지 않습니다.')
            )
            return

        # 사용자 확인
        if not options['force'] and (artworks_to_migrate.exists() or clients_to_migrate.exists()):
            confirm = input('\n위 데이터를 test2 갤러리로 이동하시겠습니까? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write('작업이 취소되었습니다.')
                return

        # 실제 마이그레이션 수행
        with transaction.atomic():
            artwork_updated = 0
            client_updated = 0
            
            # 작품 데이터 마이그레이션
            for artwork in artworks_to_migrate:
                old_gallery = artwork.gallery
                artwork.gallery = test2_gallery
                artwork.save()
                artwork_updated += 1
                
                if old_gallery:
                    self.stdout.write(f'작품 "{artwork.title_ko}": {old_gallery.name} → {test2_gallery.name}')
                else:
                    self.stdout.write(f'작품 "{artwork.title_ko}": 없음 → {test2_gallery.name}')
            
            # 고객 데이터 마이그레이션
            for client in clients_to_migrate:
                old_gallery = client.gallery
                client.gallery = test2_gallery
                client.save()
                client_updated += 1
                
                if old_gallery:
                    self.stdout.write(f'고객 "{client.name}": {old_gallery.name} → {test2_gallery.name}')
                else:
                    self.stdout.write(f'고객 "{client.name}": 없음 → {test2_gallery.name}')

        # 결과 출력
        self.stdout.write(
            self.style.SUCCESS(
                f'\n마이그레이션 완료: 작품 {artwork_updated}개, 고객 {client_updated}개가 test2 갤러리로 이동되었습니다.'
            )
        )
        
        # 최종 상태 확인
        self.stdout.write('\n=== 마이그레이션 후 상태 ===')
        test2_artworks = Artwork.objects.filter(gallery=test2_gallery).count()
        test2_clients = Client.objects.filter(gallery=test2_gallery).count()
        self.stdout.write(f'test2 갤러리 작품 수: {test2_artworks}개')
        self.stdout.write(f'test2 갤러리 고객 수: {test2_clients}개')
        
        null_artworks = Artwork.objects.filter(gallery__isnull=True).count()
        null_clients = Client.objects.filter(gallery__isnull=True).count()
        self.stdout.write(f'갤러리 없는 작품: {null_artworks}개')
        self.stdout.write(f'갤러리 없는 고객: {null_clients}개')