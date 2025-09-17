    async def _comprehensive_analysis(self) -> bool:
        """종합 분석 (5개 영역 통합) - 현재 사용 불가"""
        console.print(Panel("[bold yellow]⚠️ 기능 사용 제한[/bold yellow]", border_style="yellow"))
        console.print("\n[bold red]🚫 종합 분석 기능은 현재 사용할 수 없습니다.[/bold red]")
        console.print("[yellow]💡 이 기능은 시스템 안정성을 위해 일시적으로 비활성화되었습니다.[/yellow]")
        console.print("[dim]   대신 다른 분석 옵션을 사용해 주세요:[/dim]")
        console.print("[cyan]   • 5번: 특정 종목 분석[/cyan]")
        console.print("[cyan]   • 6번: 뉴스 재료 분석[/cyan]")
        console.print("[cyan]   • 9번: AI 종합 시장 분석[/cyan]")
        console.print("\n[dim]메인 메뉴로 돌아가려면 아무 키나 누르세요...[/dim]")
        
        # 사용자 입력 대기 (Enter 키 대기)
        try:
            input()
        except EOFError:
            # EOF 에러가 발생해도 정상적으로 처리
            pass
        except Exception:
            # 다른 예외가 발생해도 정상적으로 처리
            pass
        
        return True