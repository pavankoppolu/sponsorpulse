import React, { useState, useEffect } from 'react';
import {
  DragDropContext,
  Droppable,
  DropResult,
} from '@hello-pangea/dnd';
import {
  KanbanStage,
  KanbanBoard as KanbanBoardType,
  Outreach,
} from '../types';
import KanbanCard from './KanbanCard';
import { kanbanApi } from '../services/api';
import {
  Compass,
  Sparkles,
  FileText,
  SendHorizontal,
  MailCheck,
  MessageCircle,
} from 'lucide-react';

interface ColumnConfig {
  id: KanbanStage;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  dotColor: string;
}

const COLUMNS: ColumnConfig[] = [
  {
    id: 'DISCOVERED',
    title: 'Discovered',
    icon: Compass,
    dotColor: 'bg-sky-400',
  },
  {
    id: 'ENRICHED',
    title: 'Enriched',
    icon: Sparkles,
    dotColor: 'bg-indigo-400',
  },
  {
    id: 'DRAFTED',
    title: 'Drafted',
    icon: FileText,
    dotColor: 'bg-amber-400',
  },
  {
    id: 'READY_TO_SEND',
    title: 'Ready to Send',
    icon: SendHorizontal,
    dotColor: 'bg-teal-400',
  },
  {
    id: 'SENT',
    title: 'Sent',
    icon: MailCheck,
    dotColor: 'bg-blue-400',
  },
  {
    id: 'REPLIED',
    title: 'Replied',
    icon: MessageCircle,
    dotColor: 'bg-emerald-400',
  },
];

interface KanbanBoardProps {
  initialBoard: KanbanBoardType;
  onRefresh: () => void;
  onOpenDraftModal: (outreach: Outreach) => void;
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({
  initialBoard,
  onRefresh,
  onOpenDraftModal,
}) => {
  const [board, setBoard] = useState<KanbanBoardType>(initialBoard);

  useEffect(() => {
    setBoard(initialBoard);
  }, [initialBoard]);

  const onDragEnd = async (result: DropResult) => {
    const { source, destination, draggableId } = result;

    if (!destination) return;
    if (
      source.droppableId === destination.droppableId &&
      source.index === destination.index
    ) {
      return;
    }

    const sourceStage = source.droppableId as KanbanStage;
    const destStage = destination.droppableId as KanbanStage;
    const outreachId = Number(draggableId);

    // Deep clone state for optimistic update
    const previousBoard = { ...board };
    const newBoard: KanbanBoardType = { ...board };

    const sourceList = Array.from(newBoard[sourceStage] || []);
    const [movedItem] = sourceList.splice(source.index, 1);

    if (!movedItem) return;

    const updatedItem: Outreach = {
      ...movedItem,
      kanban_stage: destStage,
      updated_at: new Date().toISOString(),
    };

    if (sourceStage === destStage) {
      sourceList.splice(destination.index, 0, updatedItem);
      newBoard[sourceStage] = sourceList;
    } else {
      const destList = Array.from(newBoard[destStage] || []);
      destList.splice(destination.index, 0, updatedItem);
      newBoard[sourceStage] = sourceList;
      newBoard[destStage] = destList;
    }

    // Optimistically apply state
    setBoard(newBoard);

    try {
      await kanbanApi.moveKanbanCard(outreachId, destStage);
      onRefresh();
    } catch (err) {
      console.error('Failed to move kanban card:', err);
      // Revert optimistic update on failure
      setBoard(previousBoard);
      alert('Failed to update stage on the server.');
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <DragDropContext onDragEnd={onDragEnd}>
        <div className="flex-1 overflow-x-auto overflow-y-hidden p-2 sm:p-4 pb-4 sm:pb-6 snap-x snap-mandatory scroll-smooth">
          <div className="flex gap-3 sm:gap-4 h-full min-w-max">
            {COLUMNS.map((column) => {
              const cards = board[column.id] || [];
              const Icon = column.icon;

              return (
                <div
                  key={column.id}
                  className="w-[84vw] sm:w-80 flex-shrink-0 snap-center flex flex-col bg-slate-900/40 border border-slate-800/80 rounded-2xl overflow-hidden shadow-sm backdrop-blur-sm"
                >
                  {/* Refined Column Header */}
                  <div className="px-4 py-3 border-b border-slate-800/80 bg-slate-900/70 flex items-center justify-between">
                    <div className="flex items-center space-x-2.5">
                      <span className={`w-2 h-2 rounded-full ${column.dotColor}`} />
                      <Icon className="w-3.5 h-3.5 text-slate-400" />
                      <h3 className="text-xs font-semibold text-slate-200 tracking-wide">
                        {column.title}
                      </h3>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-slate-800 text-slate-400 border border-slate-700/60">
                      {cards.length}
                    </span>
                  </div>

                  {/* Droppable Area */}
                  <Droppable droppableId={column.id}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                        className={`flex-1 p-3 overflow-y-auto transition-colors duration-150 ${
                          snapshot.isDraggingOver
                            ? 'bg-slate-800/50 ring-2 ring-indigo-500/20 ring-inset'
                            : 'bg-transparent'
                        }`}
                      >
                        {cards.length === 0 ? (
                          <div className="h-32 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-xl text-center p-4">
                            <p className="text-xs text-slate-500 font-medium">
                              No companies in {column.title}
                            </p>
                            <p className="text-[10px] text-slate-600 mt-0.5">
                              Drag cards here
                            </p>
                          </div>
                        ) : (
                          cards.map((outreach, index) => (
                            <KanbanCard
                              key={outreach.id}
                              outreach={outreach}
                              index={index}
                              onRefresh={onRefresh}
                              onOpenDraftModal={onOpenDraftModal}
                            />
                          ))
                        )}
                        {provided.placeholder}
                      </div>
                    )}
                  </Droppable>
                </div>
              );
            })}
          </div>
        </div>
      </DragDropContext>
    </div>
  );
};

export default KanbanBoard;
