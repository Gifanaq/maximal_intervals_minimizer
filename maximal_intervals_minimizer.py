"""
АЛГОРИТМ МАКСИМАЛЬНЫХ ИНТЕРВАЛОВ ДЛЯ МИНИМИЗАЦИИ ЧАСТИЧНЫХ БУЛЕВЫХ ФУНКЦИЙ
Реализация с использованием только побитовых операций
"""

class PartialBooleanFunction:
    """
    Класс для представления частичной булевой функции.
    Хранит данные в виде битовых масок для единичных и безразличных значений.
    """
    def __init__(self, n: int, ones: list[int], dcares: list[int]):
        """
        Инициализация частичной булевой функции.
        
        Args:
            n: количество переменных
            ones: список десятичных значений для наборов, где функция = 1
            dcares: список десятичных значений для наборов "don't care"
        """
        self.n = n  # количество переменных
        self.total_points = 1 << n  # всего возможных наборов (2^n)
        
        # Преобразуем списки в битовые маски
        self.ones_mask = 0
        self.dcares_mask = 0
        
        for val in ones:
            if 0 <= val < self.total_points:
                self.ones_mask |= (1 << val)
        
        for val in dcares:
            if 0 <= val < self.total_points:
                self.dcares_mask |= (1 << val)
        
        # Все значимые наборы (единицы + безразличия)
        self.significant_mask = self.ones_mask | self.dcares_mask
        
        # Маска нулевых наборов (где функция точно = 0)
        self.zeros_mask = ((1 << self.total_points) - 1) & ~self.significant_mask
        
        # Валидация
        if self.ones_mask & self.dcares_mask:
            raise ValueError("Наборы ones и dcares не должны пересекаться")
    
    def __str__(self) -> str:
        """Строковое представление функции."""
        result = []
        result.append(f"Частичная булева функция от {self.n} переменных:")
        result.append(f"Единичные наборы:    {self._mask_to_set_str(self.ones_mask)}")
        result.append(f"Безразличные наборы: {self._mask_to_set_str(self.dcares_mask)}")
        result.append(f"Нулевые наборы:      {self._mask_to_set_str(self.zeros_mask)}")
        return "\n".join(result)
    
    def _mask_to_set_str(self, mask: int) -> str:
        """Преобразует битовую маску в строку множества."""
        if mask == 0:
            return "∅"
        
        values = []
        for i in range(self.total_points):
            if mask & (1 << i):
                values.append(f"{i}")
        return "{" + ", ".join(values[:10]) + ("..." if len(values) > 10 else "") + "}"
    
    def get_binary_representation(self) -> str:
        """Возвращает табличное представление функции."""
        lines = []
        lines.append(f"{'Набор':^{self.n+2}} | {'Значение':^12}")
        lines.append("-" * (self.n + 17))
        
        for i in range(min(self.total_points, 32)):  # Ограничиваем вывод
            binary = format(i, f'0{self.n}b')
            if self.ones_mask & (1 << i):
                value = "1"
            elif self.dcares_mask & (1 << i):
                value = "X (dc)"
            else:
                value = "0"
            lines.append(f"{binary:^{self.n+2}} | {value:^12}")
        
        if self.total_points > 32:
            lines.append(f"... и ещё {self.total_points - 32} наборов")
        
        return "\n".join(lines)


class BooleanInterval:
    """
    Класс для представления булева интервала (конъюнктивного терма).
    Интервал задается парой масок (mask, value).
    """
    def __init__(self, n: int, mask: int = 0, value: int = 0):
        """
        Инициализация интервала.
        
        Args:
            n: количество переменных
            mask: маска переменных в терме (1 - переменная присутствует)
            value: значения переменных (1 - без отрицания, 0 - с отрицанием)
        """
        self.n = n
        self.mask = mask & ((1 << n) - 1)  # Ограничиваем n битами
        self.value = value & self.mask     # Значения только для присутствующих переменных
    
    def __str__(self) -> str:
        """Строковое представление интервала в виде конъюнкции."""
        if self.mask == 0:
            return "1"  # Константа 1
        
        terms = []
        # Переменные от старшей (индекс n-1) к младшей (индекс 0)
        for i in range(self.n - 1, -1, -1):
            if self.mask & (1 << i):
                # Используем буквы: x1, x2, ..., xn
                var_name = f"x{self.n - i}"
                if self.value & (1 << i):
                    terms.append(var_name)
                else:
                    terms.append(f"¬{var_name}")
        
        return " & ".join(terms)
    
    def __eq__(self, other) -> bool:
        return (self.n == other.n and 
                self.mask == other.mask and 
                self.value == other.value)
    
    def __hash__(self) -> int:
        return hash((self.n, self.mask, self.value))
    
    def __lt__(self, other) -> bool:
        """Сравнение для сортировки по размеру интервала."""
        return self.size() > other.size()  # Сначала большие интервалы
    
    def covers_point(self, point: int) -> bool:
        """
        Проверяет, покрывает ли интервал данную точку.
        
        Точка point покрывается интервалом, если для всех переменных,
        присутствующих в интервале (mask[i]=1), значение в точке совпадает
        со значением в интервале (value[i]).
        
        Формально: (point & mask) == value
        """
        return (point & self.mask) == self.value
    
    def covers_mask(self, mask: int) -> int:
        """
        Возвращает битовую маску точек из заданной маски, покрываемых интервалом.
        Оптимизированная версия без явного перебора всех точек.
        """
        result = 0
        
        # Если интервал покрывает всё (mask=0)
        if self.mask == 0:
            return mask
        
        # Генерируем все точки интервала
        free_vars = ((1 << self.n) - 1) ^ self.mask  # Свободные переменные
        free_count = self.n - bin(self.mask).count('1')
        
        # Перебираем все комбинации свободных переменных
        for free_val in range(1 << free_count):
            # Собираем точку
            point = self.value
            temp_free = free_vars
            temp_val = free_val
            
            for _ in range(free_count):
                if temp_free == 0:
                    break
                lsb = temp_free & -temp_free
                if temp_val & 1:
                    point |= lsb
                temp_free ^= lsb
                temp_val >>= 1
            
            # Проверяем, есть ли эта точка в mask
            if point < (1 << self.n) and (mask & (1 << point)):
                result |= (1 << point)
        
        return result
    
    def get_all_points_mask(self) -> int:
        """Возвращает маску всех точек, покрываемых интервалом."""
        if self.mask == 0:
            return (1 << (1 << self.n)) - 1  # Все точки
        
        result = 0
        free_vars = ((1 << self.n) - 1) ^ self.mask
        free_count = self.n - bin(self.mask).count('1')
        
        # Перебираем все комбинации свободных переменных
        for free_val in range(1 << free_count):
            point = self.value
            temp_free = free_vars
            temp_val = free_val
            
            for _ in range(free_count):
                if temp_free == 0:
                    break
                lsb = temp_free & -temp_free
                if temp_val & 1:
                    point |= lsb
                temp_free ^= lsb
                temp_val >>= 1
            
            if point < (1 << self.n):
                result |= (1 << point)
        
        return result
    
    def is_subset_of(self, other: 'BooleanInterval') -> bool:
        """
        Проверяет, является ли текущий интервал подмножеством другого.
        """
        return ((self.mask & other.mask) == other.mask and
                (self.value & other.mask) == other.value)
    
    def expand(self, allowed_mask: int) -> list['BooleanInterval']:
        """
        Расширяет интервал, убирая одну переменную.
        Возвращает список допустимых расширений.
        """
        expansions = []
        
        # Получаем все точки текущего интервала
        current_points_mask = self.get_all_points_mask()
        
        # Для каждой переменной в интервале
        vars_in_interval = self.mask
        while vars_in_interval:
            # Берём одну переменную
            var_bit = vars_in_interval & -vars_in_interval
            
            # Убираем её
            new_mask = self.mask ^ var_bit
            new_value = self.value & new_mask
            
            # Создаём новый интервал
            new_interval = BooleanInterval(self.n, new_mask, new_value)
            
            # Получаем все точки нового интервала
            new_points_mask = new_interval.get_all_points_mask()
            
            # Проверяем: новые точки (которых не было в старом интервале)
            # должны входить в allowed_mask
            new_points = new_points_mask & ~current_points_mask
            
            # Если все новые точки в allowed_mask, то расширение допустимо
            if (new_points & ~allowed_mask) == 0:
                expansions.append(new_interval)
            
            vars_in_interval ^= var_bit
        
        return expansions
    
    def size(self) -> int:
        """Возвращает количество точек в интервале."""
        # Количество свободных переменных = n - количество фиксированных
        fixed_vars = bin(self.mask).count('1')
        return 1 << (self.n - fixed_vars)


class MaximalIntervalsMinimizer:  
    """
    Реализация алгоритма максимальных интервалов.
    """
    def __init__(self, func: PartialBooleanFunction):
        self.func = func
        self.n = func.n
        self.all_intervals = []
        self.essential_intervals = []  
    
    def find_all_max_intervals(self) -> list[BooleanInterval]:
        """
        Находит все максимальные интервалы.
        Использует поиск в ширину (BFS).
        """
        # Начинаем с минимальных интервалов (точек) из significant_mask
        start_intervals = []
        significant_mask = self.func.significant_mask
        
        # Создаём интервалы для каждой значимой точки
        temp = significant_mask
        while temp:
            lsb = temp & -temp
            point = lsb.bit_length() - 1
            
            # Интервал, фиксирующий все переменные для этой точки
            full_mask = (1 << self.n) - 1
            interval = BooleanInterval(self.n, full_mask, point)
            start_intervals.append(interval)
            
            temp ^= lsb
        
        # Поиск в ширину
        from collections import deque
        
        queue = deque(start_intervals)
        visited = set()
        max_intervals = []
        
        while queue:
            current = queue.popleft()
            
            if current in visited:
                continue
            visited.add(current)
            
            
            expansions = current.expand(significant_mask)
            
            if expansions:
                
                for exp in expansions:
                    if exp not in visited:
                        queue.append(exp)
            else:
                # Интервал максимален
                # Проверяем, что он покрывает хотя бы одну единицу
                if current.covers_mask(self.func.ones_mask) != 0:
                    max_intervals.append(current)
        
        # Удаляем дубликаты и подмножества
        unique_intervals = []
        for i, interval in enumerate(max_intervals):
            is_subset = False
            for j, other in enumerate(max_intervals):
                if i != j and interval.is_subset_of(other):
                    is_subset = True
                    break
            if not is_subset:
                unique_intervals.append(interval)
        
        # Сортируем по размеру (от большего к меньшему)
        unique_intervals.sort()
        
        self.all_intervals = unique_intervals
        return unique_intervals
    
    def find_essential_intervals(self) -> list[BooleanInterval]:  
        """
        Находит обязательные интервалы (покрывающие хотя бы одну единицу,
        не покрываемую другими интервалами).
        """
        if not self.all_intervals:
            self.find_all_max_intervals()
        
        # Для каждой единицы находим, какие интервалы её покрывают
        coverage_map = {}
        
        # Инициализируем для всех единичных точек
        ones_points = []
        temp = self.func.ones_mask
        while temp:
            lsb = temp & -temp
            point = lsb.bit_length() - 1
            ones_points.append(point)
            coverage_map[point] = []
            temp ^= lsb
        
        # Заполняем карту покрытия
        for interval in self.all_intervals:
            covered = interval.covers_mask(self.func.ones_mask)
            
            temp = covered
            while temp:
                lsb = temp & -temp
                point = lsb.bit_length() - 1
                if point in coverage_map:
                    coverage_map[point].append(interval)
                temp ^= lsb
        
        # Находим обязательные интервалы (единственные для покрытия точки)
        essential_intervals = []  # ← ИЗМЕНЕНО НАЗВАНИЕ!
        covered_mask = 0
        
        # Этап 1: интервалы, единственные для покрытия некоторых точек
        for point, intervals in coverage_map.items():
            if len(intervals) == 1:
                interval = intervals[0]
                if interval not in essential_intervals:
                    essential_intervals.append(interval)
                    covered_mask |= interval.covers_mask(self.func.ones_mask)
        
        # Этап 2: жадное добавление оставшихся интервалов
        remaining_mask = self.func.ones_mask & ~covered_mask
        
        while remaining_mask:
            best_interval = None
            best_coverage = 0
            
            for interval in self.all_intervals:
                if interval in essential_intervals:
                    continue
                
                coverage = interval.covers_mask(remaining_mask)
                coverage_count = bin(coverage).count('1')
                
                if coverage_count > best_coverage:
                    best_coverage = coverage_count
                    best_interval = interval
            
            if best_interval:
                essential_intervals.append(best_interval)
                covered_mask |= best_interval.covers_mask(self.func.ones_mask)
                remaining_mask = self.func.ones_mask & ~covered_mask
            else:
                break
        
        self.essential_intervals = essential_intervals  
        return essential_intervals
    
    def minimize(self) -> list[BooleanInterval]:
        """
        Основной метод минимизации.
        """
        print("🔍 Поиск всех максимальных интервалов...")
        max_intervals = self.find_all_max_intervals()
        
        print(f"✅ Найдено {len(max_intervals)} максимальных интервалов:")
        for i, interval in enumerate(max_intervals, 1):
            covered_ones = interval.covers_mask(self.func.ones_mask)
            ones_count = bin(covered_ones).count('1')
            size = interval.size()
            print(f"   {i:2}. {str(interval):30} | размер: {size:2} | покрывает {ones_count} единиц")
        
        print("\n🎯 Определение обязательных интервалов...")  
        essential_intervals = self.find_essential_intervals()  
        
        # Проверяем покрытие
        covered_mask = 0
        for interval in essential_intervals:
            covered_mask |= interval.covers_mask(self.func.ones_mask)
        
        if covered_mask == self.func.ones_mask:
            print(f"✓ Все единичные наборы покрыты {len(essential_intervals)} интервалами!")
            result = essential_intervals
        else:
            print(f"⚠ Обязательные интервалы покрывают только {bin(covered_mask).count('1')} из {bin(self.func.ones_mask).count('1')} единиц")
            print("  Применяем жадный алгоритм покрытия...")
            result = self._greedy_cover(max_intervals)
        
        return result
    
    def _greedy_cover(self, intervals: list[BooleanInterval]) -> list[BooleanInterval]:
        """
        Жадный алгоритм покрытия.
        """
        uncovered = self.func.ones_mask
        result = []
        
        while uncovered:
            best_interval = None
            best_coverage = 0
            
            for interval in intervals:
                if interval in result:
                    continue
                
                coverage = interval.covers_mask(uncovered)
                coverage_count = bin(coverage).count('1')
                
                if coverage_count > best_coverage:
                    best_coverage = coverage_count
                    best_interval = interval
            
            if best_interval and best_coverage > 0:
                result.append(best_interval)
                uncovered &= ~best_interval.covers_mask(self.func.ones_mask)
            else:
                break
        
        return result
    
    def get_minimal_dnf(self) -> str:
        """
        Возвращает минимальную ДНФ в виде строки.
        """
        min_intervals = self.minimize()
        
        if not min_intervals:
            return "0"
        
        terms = []
        for interval in min_intervals:
            term = str(interval)
            if term == "1":
                return "1"
            terms.append(f"({term})")
        
        return " ∨ ".join(terms)


# ============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ 
# ============================================================================

def example_1():
    """Пример 1: Простая функция от 3 переменных"""
    print("=" * 70)
    print("ПРИМЕР 1: f(x1, x2, x3)")
    print("Единичные наборы: 0, 1, 2, 3, 6")
    print("Безразличные наборы: 4, 5")
    print("=" * 70)
    
    # Создаём функцию
    func = PartialBooleanFunction(
        n=3,
        ones=[0, 1, 2, 3, 6],    # 000, 001, 010, 011, 110
        dcares=[4, 5]            # 100, 101
    )
    
    print(func.get_binary_representation())
    print()
    
    # Минимизируем
    minimizer = MaximalIntervalsMinimizer(func)  
    result = minimizer.get_minimal_dnf()
    
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ МИНИМИЗАЦИИ:")
    print(f"Минимальная ДНФ: F = {result}")
    print("=" * 70)


def example_2():
    """Пример 2: Частичная функция от 3 переменных"""
    print("\n\n" + "=" * 70)
    print("ПРИМЕР 2: f(x1, x2, x3)")
    print("Единичные наборы: 2, 3, 6, 7")
    print("Безразличные наборы: 0, 1")
    print("=" * 70)
    
    func = PartialBooleanFunction(
        n=3,
        ones=[2, 3, 6, 7],    # 010, 011, 110, 111
        dcares=[0, 1]         # 000, 001
    )
    
    print(func.get_binary_representation())
    print()
    
    minimizer = MaximalIntervalsMinimizer(func)  
    result = minimizer.get_minimal_dnf()
    
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ МИНИМИЗАЦИИ:")
    print(f"Минимальная ДНФ: F = {result}")
    print("=" * 70)


def example_3():
    """Пример 3: Полная функция (без don't care)"""
    print("\n\n" + "=" * 70)
    print("ПРИМЕР 3: Полная функция f(x1, x2, x3)")
    print("Единичные наборы: 0, 3, 5, 6, 7")
    print("Безразличные наборы: нет")
    print("=" * 70)
    
    func = PartialBooleanFunction(
        n=3,
        ones=[0, 3, 5, 6, 7],  # 000, 011, 101, 110, 111
        dcares=[]
    )
    
    print(func.get_binary_representation())
    print()
    
    minimizer = MaximalIntervalsMinimizer(func)  
    result = minimizer.get_minimal_dnf()
    
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ МИНИМИЗАЦИИ:")
    print(f"Минимальная ДНФ: F = {result}")
    print("=" * 70)


def example_4():
    """Пример 4: Простая функция от 2 переменных для проверки"""
    print("\n\n" + "=" * 70)
    print("ПРИМЕР 4: f(x1, x2)")
    print("Единичные наборы: 0, 3")
    print("Безразличные наборы: 1")
    print("=" * 70)
    
    func = PartialBooleanFunction(
        n=2,
        ones=[0, 3],    # 00, 11
        dcares=[1]      # 01
    )
    
    print(func.get_binary_representation())
    print()
    
    minimizer = MaximalIntervalsMinimizer(func)  
    result = minimizer.get_minimal_dnf()
    
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТ МИНИМИЗАЦИИ:")
    print(f"Минимальная ДНФ: F = {result}")
    print("=" * 70)


def demonstration():
    """Демонстрация работы с побитовыми операциями"""
    print("\n\n" + "=" * 70)
    print("ДЕМОНСТРАЦИЯ РАБОТЫ С ПОБИТОВЫМИ ОПЕРАЦИЯМИ")
    print("=" * 70)
    
   
    print("\n1. Представление интервала x1 & ¬x3 (для n=3):")
    interval = BooleanInterval(n=3, mask=0b101, value=0b100)
    print(f"   mask = 0b{interval.mask:03b} = {interval.mask}")
    print(f"   value = 0b{interval.value:03b} = {interval.value}")
    print(f"   Интервал: {interval}")
    
    print("\n2. Проверка покрытия точек:")
    test_points = [0b000, 0b001, 0b100, 0b101, 0b110, 0b111]
    for point in test_points:
        binary = format(point, '03b')
        covers = interval.covers_point(point)
        print(f"   Точка {binary} ({point}): {'ПОКРЫВАЕТСЯ' if covers else 'не покрывается'}")
    
    print("\n3. Побитовые операции для проверки покрытия точки 100 (4):")
    point = 0b100
    print(f"   point = {format(point, '03b')} ({point})")
    print(f"   mask  = {format(interval.mask, '03b')}")
    print(f"   value = {format(interval.value, '03b')}")
    print(f"   point & mask = {format(point & interval.mask, '03b')}")
    print(f"   Результат: (point & mask) == value -> {(point & interval.mask) == interval.value}")


# ============================================================================
# ТЕСТИРОВАНИЕ
# ============================================================================

def run_tests():
    """Запуск всех примеров"""
    print("🚀 АЛГОРИТМ МАКСИМАЛЬНЫХ ИНТЕРВАЛОВ ДЛЯ МИНИМИЗАЦИИ ЧАСТИЧНЫХ ФУНКЦИЙ")
    print("=" * 70)
    
    example_1()
    example_2()
    example_3()
    example_4()
    demonstration()
    
    print("\n" + "=" * 70)
    print("✅ ВСЕ ПРИМЕРЫ ВЫПОЛНЕНЫ УСПЕШНО!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
