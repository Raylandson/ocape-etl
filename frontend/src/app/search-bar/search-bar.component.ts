import { Component, ElementRef, EventEmitter, HostListener, Input, OnDestroy, OnInit, Output, inject } from '@angular/core';
import { Subject, Subscription, of } from 'rxjs';
import { catchError, debounceTime, distinctUntilChanged, map, switchMap, tap } from 'rxjs/operators';
import { SearchResult, SearchService } from '../services/search.service';

export interface SearchLayerMeta {
  name: string;
  color: string;
}

interface SearchResultGroup {
  layerId: string;
  layerName: string;
  color: string;
  items: { result: SearchResult; index: number }[];
}

const MIN_QUERY_LENGTH = 3;

@Component({
  selector: 'app-search-bar',
  standalone: true,
  imports: [],
  templateUrl: './search-bar.component.html',
  styleUrl: './search-bar.component.css'
})
export class SearchBarComponent implements OnInit, OnDestroy {
  private searchService = inject(SearchService);
  private host = inject(ElementRef<HTMLElement>);

  @Input() layerMeta: Record<string, SearchLayerMeta> = {};
  @Output() resultSelected = new EventEmitter<SearchResult>();

  query: string = '';
  results: SearchResult[] = [];
  groups: SearchResultGroup[] = [];
  activeIndex: number = -1;
  isOpen: boolean = false;
  isLoading: boolean = false;
  hasError: boolean = false;

  // Query the current results belong to, so Enter never picks results of an older query
  private resultsQuery: string = '';
  private pendingEnter: boolean = false;

  private query$ = new Subject<string>();
  private subscription?: Subscription;

  ngOnInit() {
    this.subscription = this.query$
      .pipe(
        map(q => q.trim()),
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => (this.hasError = false)),
        switchMap(q => {
          if (!this.isSearchable(q)) return of({ q, results: [] as SearchResult[] });
          return this.searchService.search(q).pipe(
            map(results => ({ q, results })),
            catchError(() => {
              this.hasError = true;
              return of({ q, results: [] as SearchResult[] });
            })
          );
        })
      )
      .subscribe(({ q, results }) => {
        this.isLoading = false;
        this.resultsQuery = q;
        this.setResults(results);
        if (this.pendingEnter) {
          this.pendingEnter = false;
          if (results.length) this.select(results[0]);
        }
      });
  }

  ngOnDestroy() {
    this.subscription?.unsubscribe();
  }

  @HostListener('document:mousedown', ['$event'])
  onDocumentMouseDown(event: MouseEvent) {
    if (!this.host.nativeElement.contains(event.target as Node)) {
      this.isOpen = false;
    }
  }

  onInput(value: string) {
    this.query = value;
    this.isOpen = true;
    this.pendingEnter = false;
    this.isLoading = this.isSearchable(value.trim()) && value.trim() !== this.resultsQuery;
    this.query$.next(value);
  }

  onFocus() {
    if (this.query.trim().length > 0) this.isOpen = true;
  }

  onKeyDown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.isOpen = true;
      if (this.results.length) this.activeIndex = (this.activeIndex + 1) % this.results.length;
      this.scrollActiveIntoView();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (this.results.length) this.activeIndex = (this.activeIndex - 1 + this.results.length) % this.results.length;
      this.scrollActiveIntoView();
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (this.isLoading) {
        // Results for the typed query are still on their way; pick the top hit once they arrive
        this.pendingEnter = true;
        return;
      }
      const result = this.results[this.activeIndex >= 0 ? this.activeIndex : 0];
      if (result) this.select(result);
    } else if (event.key === 'Escape') {
      this.isOpen = false;
      (event.target as HTMLInputElement).blur();
    }
  }

  clear() {
    this.query = '';
    this.pendingEnter = false;
    this.isLoading = false;
    this.query$.next('');
    this.setResults([]);
    this.isOpen = false;
  }

  select(result: SearchResult) {
    this.isOpen = false;
    this.resultSelected.emit(result);
  }

  isSearchable(q: string): boolean {
    return q.replace(/[\W_]/g, '').length >= MIN_QUERY_LENGTH;
  }

  private setResults(results: SearchResult[]) {
    this.results = results;
    this.activeIndex = -1;

    const groups: SearchResultGroup[] = [];
    results.forEach((result, index) => {
      let group = groups.find(g => g.layerId === result.layer_id);
      if (!group) {
        const meta = this.layerMeta[result.layer_id];
        group = {
          layerId: result.layer_id,
          layerName: meta?.name ?? result.layer_id,
          color: meta?.color ?? '#64748b',
          items: []
        };
        groups.push(group);
      }
      group.items.push({ result, index });
    });
    this.groups = groups;
  }

  private scrollActiveIntoView() {
    setTimeout(() => {
      const el = this.host.nativeElement.querySelector('.search-result-item.active');
      el?.scrollIntoView({ block: 'nearest' });
    });
  }
}
